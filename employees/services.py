import requests
import json
import logging
from datetime import datetime
from django.utils import timezone
from django.db import transaction
from .models import Employee, Absence
from api_config.models import EmployeeCredentials, AbsenceCredentials, SyncLog
import concurrent.futures
from functools import partial

logger = logging.getLogger(__name__)

# ---------------------------
# Constants to avoid duplication (S1192)
# ---------------------------
NO_EMPLOYEES_FOUND_MSG = "Nenhum funcionário encontrado para sincronizar"
NO_ABSENCES_FOUND_MSG = "Nenhum registro de absenteísmo encontrado para sincronizar"
DATE_FORMAT_DDMMYYYY = "%d/%m/%Y"  # Replaces multiple occurrences of '%d/%m/%Y'

class APIService:
    """Serviço para interação com as APIs externas"""

    @staticmethod
    def sync_employees(user, client, sync_log_id=None):
        """
        Sincroniza dados de funcionários da API externa usando processamento paralelo
        """
        credentials = EmployeeCredentials.objects.filter(user=user, client=client).first()
        if not credentials:
            return {
                "success": False,
                "message": "Credenciais não encontradas. Configure suas credenciais na página de configurações."
            }

        # 1) Recuperar/criar SyncLog
        sync_log = APIService._get_or_create_log(
            sync_log_id, client, user, "employee", credentials.company
        )

        try:
            # 2) Montar parâmetros e fazer requisição
            params = APIService._build_employee_params(credentials)
            param_str = json.dumps(params)
            logger.info(f"Iniciando sincronização de funcionários para empresa {credentials.company}")
            APIService._update_sync_log_message(sync_log, "Aguardando resposta da API...")

            url = "https://ws1.soc.com.br/WebSoc/exportadados?parametro="
            response = requests.get(url=url + param_str, timeout=30)

            # 3) Verificar status da requisição
            if response.status_code != 200:
                return APIService._handle_http_error(sync_log, response)

            response_decode = response.content.decode("latin-1")
            APIService._update_sync_log_message(sync_log, "Dados recebidos, processando...")

            # 4) Decodificar JSON
            try:
                employees_data = json.loads(response_decode)
            except json.JSONDecodeError as e:
                return APIService._handle_json_decode_error(sync_log, e, response_decode)

            # 5) Verificar erro da API ou lista vazia
            if isinstance(employees_data, dict) and "Error" in employees_data:
                error_msg = f"Erro da API: {employees_data['Error']}"
                return APIService._finalize_sync_log(sync_log, "error", error_msg)

            if not employees_data:
                logger.info(NO_EMPLOYEES_FOUND_MSG)
                sync_log.status = "success"
                sync_log.error_message = NO_EMPLOYEES_FOUND_MSG
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=["status", "error_message", "end_time"])
                return {"success": True, "message": NO_EMPLOYEES_FOUND_MSG}

            # 6) Processar os dados
            total_records = len(employees_data)
            logger.info(f"Recebidos {total_records} registros de funcionários")
            sync_log.records_processed = total_records
            APIService._update_sync_log_message(
                sync_log, f"Processando {total_records} registros..."
            )

            # 7) Processamento paralelo
            result = APIService._process_employees_parallel(
                employees_data, total_records, sync_log, client
            )
            return result

        except Exception as e:
            return APIService._handle_general_exception(sync_log, e)

    @staticmethod
    def sync_absences(user, client, sync_log_id=None):
        """
        Sincroniza dados de absenteísmo da API externa usando processamento paralelo
        """
        credentials = AbsenceCredentials.objects.filter(user=user, client=client).first()
        if not credentials:
            return {
                "success": False,
                "message": "Credenciais não encontradas. Configure suas credenciais na página de configurações."
            }

        # 1) Recuperar/criar SyncLog
        sync_log = APIService._get_or_create_log(
            sync_log_id, client, user, "absence", credentials.main_company
        )

        try:
            # 2) Montar parâmetros e fazer requisição
            params = {
                "empresa": credentials.main_company,
                "codigo": credentials.code,
                "chave": credentials.key,
                "tipoSaida": "json",
                "empresaTrabalho": credentials.work_company,
                "dataInicio": credentials.start_date.strftime(DATE_FORMAT_DDMMYYYY),
                "dataFim": credentials.end_date.strftime(DATE_FORMAT_DDMMYYYY),
            }
            logger.info(f"Iniciando sincronização de absenteísmo para empresa {credentials.main_company}")
            APIService._update_sync_log_message(sync_log, "Aguardando resposta da API...")

            url = "https://ws1.soc.com.br/WebSoc/exportadados?parametro="
            param_str = json.dumps(params)
            response = requests.get(url=url + param_str, timeout=30)

            if response.status_code != 200:
                return APIService._handle_http_error(sync_log, response)

            response_decode = response.content.decode("latin-1")
            APIService._update_sync_log_message(sync_log, "Dados recebidos, processando...")

            # 3) Decodificar JSON
            try:
                absences_data = json.loads(response_decode)
            except json.JSONDecodeError as e:
                return APIService._handle_json_decode_error(sync_log, e, response_decode)

            # 4) Verificar se erro ou lista vazia
            if isinstance(absences_data, dict) and "Error" in absences_data:
                error_msg = f"Erro da API: {absences_data['Error']}"
                return APIService._finalize_sync_log(sync_log, "error", error_msg)

            if not absences_data:
                logger.info(NO_ABSENCES_FOUND_MSG)
                sync_log.status = "success"
                sync_log.error_message = NO_ABSENCES_FOUND_MSG
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=["status", "error_message", "end_time"])
                return {"success": True, "message": NO_ABSENCES_FOUND_MSG}

            # 5) Preparar e processar
            total_records = len(absences_data)
            logger.info(f"Recebidos {total_records} registros de absenteísmo")
            sync_log.records_processed = total_records
            APIService._update_sync_log_message(
                sync_log, f"Processando {total_records} registros..."
            )

            # Pré-carregar funcionários existentes
            existing_employees = APIService._preload_employees(client, absences_data)

            # 6) Processar em paralelo
            return APIService._process_absences_parallel(
                absences_data, total_records, sync_log, client, existing_employees
            )

        except Exception as e:
            return APIService._handle_general_exception(sync_log, e)

    # ----------------------------------------------------------------------
    #   HELPER METHODS
    # ----------------------------------------------------------------------

    @staticmethod
    def _get_or_create_log(sync_log_id, client, user, api_type, company):
        if sync_log_id:
            try:
                sync_log = SyncLog.objects.get(id=sync_log_id)
                sync_log.company = company
                sync_log.save(update_fields=["company"])
                return sync_log
            except SyncLog.DoesNotExist:
                pass

        # Se não existe, criar
        return SyncLog.objects.create(
            client=client,
            user=user,
            api_type=api_type,
            company=company,
            status="error",
            records_processed=0,
            records_success=0,
            records_error=0,
            start_time=timezone.now(),
        )

    @staticmethod
    def _build_employee_params(credentials):
        params = {
            "empresa": credentials.company,
            "codigo": credentials.code,
            "chave": credentials.key,
            "tipoSaida": "json",
        }
        if credentials.is_active:
            params["ativo"] = "Sim"
        if credentials.is_inactive:
            params["inativo"] = "Sim"
        if credentials.is_away:
            params["afastado"] = "Sim"
        if credentials.is_pending:
            params["pendente"] = "Sim"
        if credentials.is_vacation:
            params["ferias"] = "Sim"
        return params

    @staticmethod
    def _update_sync_log_message(sync_log, message):
        sync_log.error_message = message
        sync_log.save(update_fields=["error_message"])

    @staticmethod
    def _handle_http_error(sync_log, response):
        error_message = f"Erro na requisição: {response.status_code} - {response.text}"
        logger.error(error_message)
        sync_log.error_message = error_message
        sync_log.end_time = timezone.now()
        sync_log.save(update_fields=["error_message", "end_time"])
        return {"success": False, "message": error_message}

    @staticmethod
    def _handle_json_decode_error(sync_log, exception, response_decode):
        error_message = (
            f"Erro ao decodificar resposta JSON: {str(exception)}\n"
            f"Resposta recebida: {response_decode[:1000]}"
        )
        logger.error(error_message)
        sync_log.error_message = error_message
        sync_log.end_time = timezone.now()
        sync_log.save(update_fields=["error_message", "end_time"])
        return {
            "success": False,
            "message": "Erro ao decodificar resposta da API. Verifique as credenciais.",
        }

    @staticmethod
    def _finalize_sync_log(sync_log, status, message):
        logger.error(message)
        sync_log.error_message = message
        sync_log.status = status
        sync_log.end_time = timezone.now()
        sync_log.save(update_fields=["error_message", "status", "end_time"])
        return {"success": (False if status == "error" else True), "message": message}

    @staticmethod
    def _handle_general_exception(sync_log, exception):
        error_message = f"Erro na sincronização: {str(exception)}"
        logger.error(error_message)
        sync_log.error_message = error_message
        sync_log.end_time = timezone.now()
        sync_log.save()
        return {"success": False, "message": error_message}

    # ----------------------------
    # EMPLOYEES PROCESSING
    # ----------------------------
    @staticmethod
    def _process_employees_parallel(employees_data, total_records, sync_log, client):
        success_records = 0
        error_records = 0
        processed_count = 0
        last_update_percent = 0

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            func = partial(APIService._process_single_employee, client=client)
            futures = [executor.submit(func, data) for data in employees_data]

            for future in concurrent.futures.as_completed(futures):
                ok = False
                try:
                    ok = future.result()
                except Exception as exc:
                    logger.error(f"Erro ao processar funcionário: {exc}")

                if ok:
                    success_records += 1
                else:
                    error_records += 1

                processed_count += 1
                last_update_percent = APIService._maybe_update_progress(
                    sync_log,
                    processed_count,
                    total_records,
                    success_records,
                    error_records,
                    last_update_percent,
                )

        # Transformamos a condicional aninhada em if/elif/else:
        if error_records == 0:
            final_status = "success"
        elif success_records > 0:
            final_status = "partial"
        else:
            final_status = "error"

        sync_log.records_processed = total_records
        sync_log.records_success = success_records
        sync_log.records_error = error_records
        sync_log.status = final_status
        sync_log.error_message = None
        sync_log.end_time = timezone.now()
        sync_log.save()

        result_msg = (
            f"Sincronização concluída. Processados: {total_records}, "
            f"Sucesso: {success_records}, Erros: {error_records}"
        )
        logger.info(result_msg)
        return {
            "success": True,
            "message": result_msg,
            "total": total_records,
            "success_count": success_records,
            "error_count": error_records,
        }

    @staticmethod
    def _process_single_employee(employee_data, client):
        """Processa um único funcionário."""
        if not employee_data.get("CODIGO"):
            logger.warning(f"Funcionário sem código, ignorando: {employee_data}")
            return False

        employee_dict = APIService._map_employee(employee_data)
        try:
            Employee.objects.update_or_create(
                client=client,
                codigo=employee_dict["codigo"],
                defaults=employee_dict,
            )
            return True
        except Exception as e:
            logger.error(f"Erro ao processar funcionário: {e}")
            return False

    @staticmethod
    def _map_employee(employee_data):
        """Monta o dicionário de campos do modelo Employee."""
        return {
            "codigo_empresa": employee_data.get("CODIGOEMPRESA"),
            "nome_empresa": employee_data.get("NOMEEMPRESA"),
            "codigo": employee_data.get("CODIGO"),
            "nome": employee_data.get("NOME")
            or f"Sem Nome ({employee_data.get('CODIGO')})",
            "codigo_unidade": employee_data.get("CODIGOUNIDADE"),
            "nome_unidade": employee_data.get("NOMEUNIDADE"),
            "codigo_setor": employee_data.get("CODIGOSETOR"),
            "nome_setor": employee_data.get("NOMESETOR"),
            "codigo_cargo": employee_data.get("CODIGOCARGO"),
            "nome_cargo": employee_data.get("NOMECARGO"),
            "cbo_cargo": employee_data.get("CBOCARGO"),
            "ccusto": employee_data.get("CCUSTO"),
            "nome_centro_custo": employee_data.get("NOMECENTROCUSTO"),
            "matricula_funcionario": employee_data.get("MATRICULAFUNCIONARIO"),
            "cpf": employee_data.get("CPF"),
            "rg": employee_data.get("RG"),
            "uf_rg": employee_data.get("UFRG"),
            "orgao_emissor_rg": employee_data.get("ORGAOEMISSORRG"),
            "situacao": employee_data.get("SITUACAO"),
            "sexo": APIService._parse_int(employee_data.get("SEXO")),
            "pis": employee_data.get("PIS"),
            "ctps": employee_data.get("CTPS"),
            "serie_ctps": employee_data.get("SERIECTPS"),
            "estado_civil": APIService._parse_int(employee_data.get("ESTADOCIVIL")),
            "tipo_contratacao": APIService._parse_int(employee_data.get("TIPOCONTATACAO")),
            "data_nascimento": APIService._parse_date(employee_data.get("DATA_NASCIMENTO")),
            "data_admissao": APIService._parse_date(employee_data.get("DATA_ADMISSAO")),
            "data_demissao": APIService._parse_date(employee_data.get("DATA_DEMISSAO")),
            "endereco": employee_data.get("ENDERECO"),
            "numero_endereco": employee_data.get("NUMERO_ENDERECO"),
            "bairro": employee_data.get("BAIRRO"),
            "cidade": employee_data.get("CIDADE"),
            "uf": employee_data.get("UF"),
            "cep": employee_data.get("CEP"),
            "telefone_residencial": employee_data.get("TELEFONERESIDENCIAL"),
            "telefone_celular": employee_data.get("TELEFONECELULAR"),
            "email": employee_data.get("EMAIL"),
            "deficiente": APIService._parse_int(employee_data.get("DEFICIENTE")),
            "deficiencia": employee_data.get("DEFICIENCIA"),
            "nome_mae": employee_data.get("NM_MAE_FUNCIONARIO"),
            "data_ultima_alteracao": APIService._parse_date(employee_data.get("DATAULTALTERACAO")),
            "matricula_rh": employee_data.get("MATRICULARH"),
            "cor": APIService._parse_int(employee_data.get("COR")),
            "escolaridade": APIService._parse_int(employee_data.get("ESCOLARIDADE")),
            "naturalidade": employee_data.get("NATURALIDADE"),
            "ramal": employee_data.get("RAMAL"),
            "regime_revezamento": APIService._parse_int(employee_data.get("REGIMEREVEZAMENTO")),
            "regime_trabalho": employee_data.get("REGIMETRABALHO"),
            "tel_comercial": employee_data.get("TELCOMERCIAL"),
            "turno_trabalho": APIService._parse_int(employee_data.get("TURNOTRABALHO")),
            "rh_unidade": employee_data.get("RHUNIDADE"),
            "rh_setor": employee_data.get("RHSETOR"),
            "rh_cargo": employee_data.get("RHCARGO"),
            "rh_centro_custo_unidade": employee_data.get("RHCENTROCUSTOUNIDADE"),
        }

    @staticmethod
    def _maybe_update_progress(
        sync_log, processed_count, total_records, success_records, error_records, last_update
    ):
        """Atualiza o progresso no sync_log a cada 5% ou no fim."""
        if total_records == 0:
            return last_update
        current_percent = (processed_count / total_records) * 100

        if current_percent - last_update >= 5 or processed_count == total_records:
            last_update = current_percent
            sync_log.records_processed = total_records
            sync_log.records_success = success_records
            sync_log.records_error = error_records
            sync_log.error_message = (
                f"Processando: {processed_count}/{total_records} registros "
                f"({round(current_percent)}%)"
            )
            sync_log.save(update_fields=["records_processed","records_success","records_error","error_message"])
        return last_update

    # ----------------------------
    # ABSENCES PROCESSING
    # ----------------------------
    @staticmethod
    def _preload_employees(client, absences_data):
        """Pré-carrega funcionários com base em matrículas presentes nos absences."""
        matriculas = {a.get("MATRICULA_FUNC") for a in absences_data if a.get("MATRICULA_FUNC")}
        if not matriculas:
            return {}
        employees_qs = Employee.objects.filter(client=client, matricula_funcionario__in=list(matriculas))
        return {emp.matricula_funcionario: emp for emp in employees_qs}

    @staticmethod
    def _process_absences_parallel(absences_data, total_records, sync_log, client, existing_employees):
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            func = partial(APIService._process_single_absence, client=client, existing_employees=existing_employees)
            results = list(executor.map(func, absences_data))

        success_records = sum(1 for r in results if r)
        error_records = total_records - success_records

        # Ao invés do ternário aninhado, utilizamos if/elif/else
        if error_records == 0:
            final_status = "success"
        elif success_records > 0:
            final_status = "partial"
        else:
            final_status = "error"

        sync_log.records_processed = total_records
        sync_log.records_success = success_records
        sync_log.records_error = error_records
        sync_log.status = final_status
        sync_log.error_message = None
        sync_log.end_time = timezone.now()
        sync_log.save()

        msg = (
            f"Sincronização concluída. Processados: {total_records}, "
            f"Sucesso: {success_records}, Erros: {error_records}"
        )
        logger.info(msg)
        return {
            "success": True,
            "message": msg,
            "total": total_records,
            "success_count": success_records,
            "error_count": error_records,
        }

    @staticmethod
    def _process_single_absence(absence_data, client, existing_employees):
        try:
            # Encontrar ou criar funcionário
            employee = APIService._find_or_create_employee_for_absence(client, absence_data, existing_employees)
            absence_dict = APIService._map_absence_fields(absence_data, employee)

            # Checar datas obrigatórias
            if not absence_dict["dt_inicio_atestado"] or not absence_dict["dt_fim_atestado"]:
                logger.warning(f"Absenteísmo sem datas obrigatórias: {absence_data}")
                return False

            return APIService._update_or_create_absence(client, employee, absence_dict, absence_data)
        except Exception as e:
            logger.error(f"Erro ao processar absenteísmo: {e}")
            return False

    @staticmethod
    def _find_or_create_employee_for_absence(client, absence_data, existing_employees):
        matricula = absence_data.get("MATRICULA_FUNC")
        employee = None
        if matricula:
            employee = existing_employees.get(matricula)
            if not employee:
                employee = Employee.objects.filter(client=client, matricula_funcionario=matricula).first()

        if employee:
            return employee

        # Se não encontrou, criar genérico
        sem_matricula_code = f"SEM_MATRICULA_{hash(str(absence_data))}"
        identifier = matricula or str(abs(hash(str(absence_data)) % 10000))
        logger.info(f"Criando funcionário genérico para matrícula: {identifier}")

        new_emp = Employee.objects.create(
            client=client,
            codigo=sem_matricula_code[:20],
            nome=f"Sem Matrícula ({identifier})",
            situacao="GENERICO",
        )
        existing_employees[matricula] = new_emp
        return new_emp

    @staticmethod
    def _map_absence_fields(absence_data, employee):
        return {
            "unidade": absence_data.get("UNIDADE"),
            "setor": absence_data.get("SETOR"),
            "matricula_func": absence_data.get("MATRICULA_FUNC"),
            "dt_nascimento": APIService._parse_date(absence_data.get("DT_NASCIMENTO")),
            "sexo": APIService._parse_int(absence_data.get("SEXO")),
            "tipo_atestado": APIService._parse_int(absence_data.get("TIPO_ATESTADO")),
            "dt_inicio_atestado": APIService._parse_date(absence_data.get("DT_INICIO_ATESTADO")),
            "dt_fim_atestado": APIService._parse_date(absence_data.get("DT_FIM_ATESTADO")),
            "hora_inicio_atestado": absence_data.get("HORA_INICIO_ATESTADO"),
            "hora_fim_atestado": absence_data.get("HORA_FIM_ATESTADO"),
            "dias_afastados": APIService._parse_int(absence_data.get("DIAS_AFASTADOS")),
            "horas_afastado": absence_data.get("HORAS_AFASTADO"),
            "cid_principal": absence_data.get("CID_PRINCIPAL"),
            "descricao_cid": absence_data.get("DESCRICAO_CID"),
            "grupo_patologico": absence_data.get("GRUPO_PATOLOGICO"),
            "tipo_licenca": absence_data.get("TIPO_LICENCA"),
            "employee": employee,
        }

    @staticmethod
    def _update_or_create_absence(client, employee, absence_dict, raw_data):
        unique_fields = {
            "client": client,
            "employee": employee,
            "dt_inicio_atestado": absence_dict["dt_inicio_atestado"],
            "dt_fim_atestado": absence_dict["dt_fim_atestado"],
        }
        # Remover chaves None
        unique_fields = {k: v for k, v in unique_fields.items() if v is not None}

        if len(unique_fields) <= 1:
            logger.warning(f"Dados insuficientes para identificar absenteísmo único: {raw_data}")
            return False

        Absence.objects.update_or_create(
            **unique_fields,
            defaults=absence_dict
        )
        return True

    # ----------------------------
    # PARSE HELPERS
    # ----------------------------
    @staticmethod
    def _parse_date(date_str):
        """Converte string de data para objeto date"""
        if not date_str:
            return None
        try:
            return datetime.strptime(date_str, DATE_FORMAT_DDMMYYYY).date()
        except ValueError:
            try:
                # Tentar formato alternativo
                return datetime.strptime(date_str, "%Y-%m-%d").date()
            except ValueError:
                logger.warning(f"Formato de data inválido: {date_str}")
                return None

    @staticmethod
    def _parse_int(int_str):
        """Converte string para inteiro"""
        if not int_str:
            return None
        try:
            return int(int_str)
        except ValueError:
            logger.warning(f"Formato de número inválido: {int_str}")
            return None

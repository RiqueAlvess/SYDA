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

class APIService:
    """Serviço para interação com as APIs externas"""
    
    @staticmethod
    def sync_employees(user, client, sync_log_id=None):
        """
        Sincroniza dados de funcionários da API externa usando processamento paralelo
        """
        # Recuperar credenciais
        credentials = EmployeeCredentials.objects.filter(user=user, client=client).first()
        if not credentials:
            return {"success": False, "message": "Credenciais não encontradas. Configure suas credenciais na página de configurações."}
        
        # Recuperar ou criar log de sincronização
        if sync_log_id:
            try:
                sync_log = SyncLog.objects.get(id=sync_log_id)
                # Atualizar o log com as informações da empresa
                sync_log.company = credentials.company
                sync_log.save(update_fields=['company'])
            except SyncLog.DoesNotExist:
                # Criar log se o ID fornecido não existir
                sync_log = SyncLog.objects.create(
                    client=client,
                    user=user,
                    api_type='employee',
                    company=credentials.company,
                    status='error',
                    records_processed=0,
                    records_success=0,
                    records_error=0,
                    start_time=timezone.now()
                )
        else:
            # Criar novo log se nenhum ID for fornecido
            sync_log = SyncLog.objects.create(
                client=client,
                user=user,
                api_type='employee',
                company=credentials.company,
                status='error',
                records_processed=0,
                records_success=0,
                records_error=0,
                start_time=timezone.now()
            )
        
        try:
            # Construir parâmetros para a API
            params = {
                "empresa": credentials.company,
                "codigo": credentials.code,
                "chave": credentials.key,
                "tipoSaida": "json"
            }
            
            # Adicionar filtros de status
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
            
            # Fazer requisição à API
            url = 'https://ws1.soc.com.br/WebSoc/exportadados?parametro='
            
            # Converter o dicionário para string para passar como parâmetro
            param_str = json.dumps(params)
            
            logger.info(f"Iniciando sincronização de funcionários para empresa {credentials.company}")
            
            # Atualizar log com início da requisição
            sync_log.error_message = "Aguardando resposta da API..."
            sync_log.save(update_fields=['error_message'])
            
            response = requests.get(url=url + param_str, timeout=30)
            
            if response.status_code != 200:
                error_message = f"Erro na requisição: {response.status_code} - {response.text}"
                logger.error(error_message)
                sync_log.error_message = error_message
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['error_message', 'end_time'])
                return {"success": False, "message": error_message}
            
            # Decodificar resposta
            response_decode = response.content.decode('latin-1')
            
            # Atualizar log com recebimento dos dados
            sync_log.error_message = "Dados recebidos, processando..."
            sync_log.save(update_fields=['error_message'])
            
            try:
                employees_data = json.loads(response_decode)
            except json.JSONDecodeError as e:
                error_message = f"Erro ao decodificar resposta JSON: {str(e)}\nResposta recebida: {response_decode[:1000]}"
                logger.error(error_message)
                sync_log.error_message = error_message
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['error_message', 'end_time'])
                return {"success": False, "message": "Erro ao decodificar resposta da API. Verifique as credenciais."}
            
            # Verifica se retornou um erro
            if isinstance(employees_data, dict) and 'Error' in employees_data:
                error_message = f"Erro da API: {employees_data['Error']}"
                logger.error(error_message)
                sync_log.error_message = error_message
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['error_message', 'end_time'])
                return {"success": False, "message": error_message}
            
            # Verifica se é uma lista vazia
            if not employees_data or len(employees_data) == 0:
                logger.info("Nenhum funcionário encontrado para sincronizar")
                sync_log.status = 'success'
                sync_log.error_message = "Nenhum funcionário encontrado para sincronizar"
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['status', 'error_message', 'end_time'])
                return {"success": True, "message": "Nenhum funcionário encontrado para sincronizar"}
            
            # Log de registro encontrados
            total_records = len(employees_data)
            logger.info(f"Recebidos {total_records} registros de funcionários")
            
            # Atualizar log com quantidade de registros
            sync_log.records_processed = total_records
            sync_log.error_message = f"Processando {total_records} registros..."
            sync_log.save(update_fields=['records_processed', 'error_message'])
            
            # Função para processar um único funcionário
            def process_employee(employee_data, client):
                try:
                    # Verificar se temos o campo código
                    if not employee_data.get('CODIGO'):
                        logger.warning(f"Funcionário sem código, ignorando: {employee_data}")
                        return False
                        
                    # Mapear dados da API para o modelo
                    employee_dict = {
                        'codigo_empresa': employee_data.get('CODIGOEMPRESA'),
                        'nome_empresa': employee_data.get('NOMEEMPRESA'),
                        'codigo': employee_data.get('CODIGO'),
                        'nome': employee_data.get('NOME') or f"Sem Nome ({employee_data.get('CODIGO')})",
                        'codigo_unidade': employee_data.get('CODIGOUNIDADE'),
                        'nome_unidade': employee_data.get('NOMEUNIDADE'),
                        'codigo_setor': employee_data.get('CODIGOSETOR'),
                        'nome_setor': employee_data.get('NOMESETOR'),
                        'codigo_cargo': employee_data.get('CODIGOCARGO'),
                        'nome_cargo': employee_data.get('NOMECARGO'),
                        'cbo_cargo': employee_data.get('CBOCARGO'),
                        'ccusto': employee_data.get('CCUSTO'),
                        'nome_centro_custo': employee_data.get('NOMECENTROCUSTO'),
                        'matricula_funcionario': employee_data.get('MATRICULAFUNCIONARIO'),
                        'cpf': employee_data.get('CPF'),
                        'rg': employee_data.get('RG'),
                        'uf_rg': employee_data.get('UFRG'),
                        'orgao_emissor_rg': employee_data.get('ORGAOEMISSORRG'),
                        'situacao': employee_data.get('SITUACAO'),
                        'sexo': APIService._parse_int(employee_data.get('SEXO')),
                        'pis': employee_data.get('PIS'),
                        'ctps': employee_data.get('CTPS'),
                        'serie_ctps': employee_data.get('SERIECTPS'),
                        'estado_civil': APIService._parse_int(employee_data.get('ESTADOCIVIL')),
                        'tipo_contratacao': APIService._parse_int(employee_data.get('TIPOCONTATACAO')),
                        'data_nascimento': APIService._parse_date(employee_data.get('DATA_NASCIMENTO')),
                        'data_admissao': APIService._parse_date(employee_data.get('DATA_ADMISSAO')),
                        'data_demissao': APIService._parse_date(employee_data.get('DATA_DEMISSAO')),
                        'endereco': employee_data.get('ENDERECO'),
                        'numero_endereco': employee_data.get('NUMERO_ENDERECO'),
                        'bairro': employee_data.get('BAIRRO'),
                        'cidade': employee_data.get('CIDADE'),
                        'uf': employee_data.get('UF'),
                        'cep': employee_data.get('CEP'),
                        'telefone_residencial': employee_data.get('TELEFONERESIDENCIAL'),
                        'telefone_celular': employee_data.get('TELEFONECELULAR'),
                        'email': employee_data.get('EMAIL'),
                        'deficiente': APIService._parse_int(employee_data.get('DEFICIENTE')),
                        'deficiencia': employee_data.get('DEFICIENCIA'),
                        'nome_mae': employee_data.get('NM_MAE_FUNCIONARIO'),
                        'data_ultima_alteracao': APIService._parse_date(employee_data.get('DATAULTALTERACAO')),
                        'matricula_rh': employee_data.get('MATRICULARH'),
                        'cor': APIService._parse_int(employee_data.get('COR')),
                        'escolaridade': APIService._parse_int(employee_data.get('ESCOLARIDADE')),
                        'naturalidade': employee_data.get('NATURALIDADE'),
                        'ramal': employee_data.get('RAMAL'),
                        'regime_revezamento': APIService._parse_int(employee_data.get('REGIMEREVEZAMENTO')),
                        'regime_trabalho': employee_data.get('REGIMETRABALHO'),
                        'tel_comercial': employee_data.get('TELCOMERCIAL'),
                        'turno_trabalho': APIService._parse_int(employee_data.get('TURNOTRABALHO')),
                        'rh_unidade': employee_data.get('RHUNIDADE'),
                        'rh_setor': employee_data.get('RHSETOR'),
                        'rh_cargo': employee_data.get('RHCARGO'),
                        'rh_centro_custo_unidade': employee_data.get('RHCENTROCUSTOUNIDADE'),
                    }
                    
                    # Usar get_or_create para processar individualmente com menor bloqueio de banco
                    employee, created = Employee.objects.update_or_create(
                        client=client,
                        codigo=employee_dict['codigo'],
                        defaults=employee_dict
                    )
                    
                    return True
                except Exception as e:
                    logger.error(f"Erro ao processar funcionário: {str(e)}")
                    return False
            
            # Dividir os dados em lotes para atualização por lotes
            batch_size = min(100, max(1, total_records // 10)) 
            success_records = 0
            error_records = 0
            processed_count = 0
            last_update_percent = 0 

            # Usar ThreadPoolExecutor para processamento paralelo
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Criar uma função parcial que inclui o client como parâmetro
                process_func = partial(process_employee, client=client)
                
                # Submeter tarefas
                futures = []
                for employee_data in employees_data:
                    futures.append(executor.submit(process_func, employee_data))
                
                # Monitorar progresso
                for i, future in enumerate(concurrent.futures.as_completed(futures)):
                    try:
                        success = future.result()
                        success_records += 1 if success else 0
                        error_records += 0 if success else 1
                    except Exception as e:
                        error_records += 1
                        logger.error(f"Erro ao processar funcionário: {str(e)}")
                    
                    processed_count += 1
                    current_percent = (processed_count / total_records) * 100
                    
                    # Atualizar a cada 5% de progresso
                    if current_percent - last_update_percent >= 5 or processed_count == total_records:
                        last_update_percent = current_percent
                        # Atualizar o log com o progresso atual
                        sync_log.records_processed = total_records
                        sync_log.records_success = success_records
                        sync_log.records_error = error_records
                        sync_log.error_message = f"Processando: {processed_count}/{total_records} registros ({round(current_percent)}%)"
                        sync_log.save(update_fields=['records_processed', 'records_success', 'records_error', 'error_message'])
                
                # Atualizar o log com os resultados finais
                sync_log.records_processed = total_records
                sync_log.records_success = success_records
                sync_log.records_error = error_records
                sync_log.status = 'success' if error_records == 0 else 'partial' if success_records > 0 else 'error'
                sync_log.error_message = None  # Limpa mensagem de erro pois foi concluído
                sync_log.end_time = timezone.now()
                sync_log.save()
            
            result_message = f"Sincronização concluída. Processados: {total_records}, Sucesso: {success_records}, Erros: {error_records}"
            logger.info(result_message)
            
            return {
                "success": True,
                "message": result_message,
                "total": total_records,
                "success_count": success_records,
                "error_count": error_records
            }
            
        except Exception as e:
            error_message = f"Erro na sincronização: {str(e)}"
            logger.error(error_message)
            
            # Atualizar log de sincronização
            sync_log.error_message = error_message
            sync_log.end_time = timezone.now()
            sync_log.save()
            
            return {"success": False, "message": error_message}
    
    @staticmethod
    def sync_absences(user, client, sync_log_id=None):
        """
        Sincroniza dados de absenteísmo da API externa usando processamento paralelo
        """
        # Recuperar credenciais
        credentials = AbsenceCredentials.objects.filter(user=user, client=client).first()
        if not credentials:
            return {"success": False, "message": "Credenciais não encontradas. Configure suas credenciais na página de configurações."}
        
        # Recuperar ou criar log de sincronização
        if sync_log_id:
            try:
                sync_log = SyncLog.objects.get(id=sync_log_id)
                # Atualizar o log com as informações da empresa
                sync_log.company = credentials.main_company
                sync_log.save(update_fields=['company'])
            except SyncLog.DoesNotExist:
                # Criar log se o ID fornecido não existir
                sync_log = SyncLog.objects.create(
                    client=client,
                    user=user,
                    api_type='absence',
                    company=credentials.main_company,
                    status='error',
                    records_processed=0,
                    records_success=0,
                    records_error=0,
                    start_time=timezone.now()
                )
        else:
            # Criar novo log se nenhum ID for fornecido
            sync_log = SyncLog.objects.create(
                client=client,
                user=user,
                api_type='absence',
                company=credentials.main_company,
                status='error',
                records_processed=0,
                records_success=0,
                records_error=0,
                start_time=timezone.now()
            )
        
        try:
            # Construir parâmetros para a API
            params = {
                "empresa": credentials.main_company,
                "codigo": credentials.code,
                "chave": credentials.key,
                "tipoSaida": "json",
                "empresaTrabalho": credentials.work_company,
                "dataInicio": credentials.start_date.strftime('%d/%m/%Y'),
                "dataFim": credentials.end_date.strftime('%d/%m/%Y')
            }
            
            # Fazer requisição à API
            url = 'https://ws1.soc.com.br/WebSoc/exportadados?parametro='
            
            # Converter o dicionário para string para passar como parâmetro
            param_str = json.dumps(params)
            
            logger.info(f"Iniciando sincronização de absenteísmo para empresa {credentials.main_company}")
            
            # Atualizar log com início da requisição
            sync_log.error_message = "Aguardando resposta da API..."
            sync_log.save(update_fields=['error_message'])
            
            response = requests.get(url=url + param_str, timeout=30)
            
            if response.status_code != 200:
                error_message = f"Erro na requisição: {response.status_code} - {response.text}"
                logger.error(error_message)
                sync_log.error_message = error_message
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['error_message', 'end_time'])
                return {"success": False, "message": error_message}
            
            # Decodificar resposta
            response_decode = response.content.decode('latin-1')
            
            # Atualizar log com recebimento dos dados
            sync_log.error_message = "Dados recebidos, processando..."
            sync_log.save(update_fields=['error_message'])
            
            try:
                absences_data = json.loads(response_decode)
            except json.JSONDecodeError as e:
                error_message = f"Erro ao decodificar resposta JSON: {str(e)}\nResposta recebida: {response_decode[:1000]}"
                logger.error(error_message)
                sync_log.error_message = error_message
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['error_message', 'end_time'])
                return {"success": False, "message": "Erro ao decodificar resposta da API. Verifique as credenciais."}
            
            # Verifica se retornou um erro
            if isinstance(absences_data, dict) and 'Error' in absences_data:
                error_message = f"Erro da API: {absences_data['Error']}"
                logger.error(error_message)
                sync_log.error_message = error_message
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['error_message', 'end_time'])
                return {"success": False, "message": error_message}
            
            # Verifica se é uma lista vazia
            if not absences_data or len(absences_data) == 0:
                logger.info("Nenhum registro de absenteísmo encontrado para sincronizar")
                sync_log.status = 'success'
                sync_log.error_message = "Nenhum registro de absenteísmo encontrado para sincronizar"
                sync_log.end_time = timezone.now()
                sync_log.save(update_fields=['status', 'error_message', 'end_time'])
                return {"success": True, "message": "Nenhum registro de absenteísmo encontrado para sincronizar"}
            
            # Log de registro encontrados
            total_records = len(absences_data)
            logger.info(f"Recebidos {total_records} registros de absenteísmo")
            
            # Atualizar log com quantidade de registros
            sync_log.records_processed = total_records
            sync_log.error_message = f"Processando {total_records} registros..."
            sync_log.save(update_fields=['records_processed', 'error_message'])
            
            # Pré-buscar os funcionários existentes para reduzir consultas ao banco
            existing_employees = {}
            matriculas = set(absence.get('MATRICULA_FUNC') for absence in absences_data if absence.get('MATRICULA_FUNC'))
            
            if matriculas:
                employees = Employee.objects.filter(client=client, matricula_funcionario__in=list(matriculas))
                existing_employees = {emp.matricula_funcionario: emp for emp in employees}
                logger.info(f"Pré-carregados {len(existing_employees)} funcionários")
            
            # Função para processar um único registro de absenteísmo
            def process_absence(absence_data, client, existing_employees):
                try:
                    # Verificar se existe um funcionário correspondente
                    matricula = absence_data.get('MATRICULA_FUNC')
                    employee = None
                    
                    if matricula:
                        # Primeiro verificar no cache de funcionários pré-carregados
                        employee = existing_employees.get(matricula)
                        
                        # Se não encontrar no cache, buscar no banco (deve ser raro após pré-carregamento)
                        if not employee:
                            employee = Employee.objects.filter(
                                client=client,
                                matricula_funcionario=matricula
                            ).first()
                    
                    # Mapear dados da API para o modelo
                    absence_dict = {
                        'unidade': absence_data.get('UNIDADE'),
                        'setor': absence_data.get('SETOR'),
                        'matricula_func': matricula,
                        'dt_nascimento': APIService._parse_date(absence_data.get('DT_NASCIMENTO')),
                        'sexo': APIService._parse_int(absence_data.get('SEXO')),
                        'tipo_atestado': APIService._parse_int(absence_data.get('TIPO_ATESTADO')),
                        'dt_inicio_atestado': APIService._parse_date(absence_data.get('DT_INICIO_ATESTADO')),
                        'dt_fim_atestado': APIService._parse_date(absence_data.get('DT_FIM_ATESTADO')),
                        'hora_inicio_atestado': absence_data.get('HORA_INICIO_ATESTADO'),
                        'hora_fim_atestado': absence_data.get('HORA_FIM_ATESTADO'),
                        'dias_afastados': APIService._parse_int(absence_data.get('DIAS_AFASTADOS')),
                        'horas_afastado': absence_data.get('HORAS_AFASTADO'),
                        'cid_principal': absence_data.get('CID_PRINCIPAL'),
                        'descricao_cid': absence_data.get('DESCRICAO_CID'),
                        'grupo_patologico': absence_data.get('GRUPO_PATOLOGICO'),
                        'tipo_licenca': absence_data.get('TIPO_LICENCA'),
                        'employee': employee
                    }
                    
                    # Se não encontrar funcionário, criar um funcionário genérico
                    if not employee:
                        # Gerar um código único para o funcionário sem matrícula
                        sem_matricula_code = f"SEM_MATRICULA_{hash(str(absence_data))}"
                        identifier = matricula or str(abs(hash(str(absence_data)) % 10000))
                        
                        logger.info(f"Criando funcionário genérico para matrícula: {identifier}")
                        
                        # Criar funcionário genérico
                        employee = Employee.objects.create(
                            client=client,
                            codigo=sem_matricula_code[:20],  # Limitar a 20 caracteres
                            nome=f"Sem Matrícula ({identifier})",
                            situacao="GENERICO"
                        )
                        
                        absence_dict['employee'] = employee
                    
                    # Verificar datas obrigatórias
                    if not absence_dict['dt_inicio_atestado'] or not absence_dict['dt_fim_atestado']:
                        logger.warning(f"Absenteísmo sem datas obrigatórias: {absence_data}")
                        return False
                    
                    # Atualizar ou criar registro de absenteísmo
                    # Usamos uma combinação de campos para identificar um registro único
                    unique_fields = {
                        'client': client,
                        'employee': absence_dict['employee'],
                        'dt_inicio_atestado': absence_dict['dt_inicio_atestado'],
                        'dt_fim_atestado': absence_dict['dt_fim_atestado']
                    }
                    
                    # Filtrar apenas campos que existem (não são None)
                    unique_fields = {k: v for k, v in unique_fields.items() if v is not None}
                    
                    if len(unique_fields) > 1:  # Precisamos de pelo menos client e mais um campo
                        absence, created = Absence.objects.update_or_create(
                            **unique_fields,
                            defaults=absence_dict
                        )
                        return True
                    else:
                        logger.warning(f"Dados insuficientes para identificar absenteísmo único: {absence_data}")
                        return False
                    
                except Exception as e:
                    logger.error(f"Erro ao processar absenteísmo: {str(e)}")
                    return False
            
            # Usar ThreadPoolExecutor para processamento paralelo
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                # Criar uma função parcial que inclui os parâmetros necessários
                process_func = partial(process_absence, client=client, existing_employees=existing_employees)
                
                # Submeter as tarefas ao executor
                futures = list(executor.map(process_func, absences_data))
                
                # Contar sucessos e erros
                success_records = sum(1 for result in futures if result)
                error_records = total_records - success_records
                
                # Atualizar log de sincronização
                sync_log.records_processed = total_records
                sync_log.records_success = success_records
                sync_log.records_error = error_records
                sync_log.status = 'success' if error_records == 0 else 'partial' if success_records > 0 else 'error'
                sync_log.error_message = None  # Limpa mensagem de erro pois foi concluído com sucesso
                sync_log.end_time = timezone.now()
                sync_log.save()
                
                result_message = f"Sincronização concluída. Processados: {total_records}, Sucesso: {success_records}, Erros: {error_records}"
                logger.info(result_message)
                
                return {
                    "success": True,
                    "message": result_message,
                    "total": total_records,
                    "success_count": success_records,
                    "error_count": error_records
                }
                
        except Exception as e:
            error_message = f"Erro na sincronização: {str(e)}"
            logger.error(error_message)
            
            # Atualizar log de sincronização
            sync_log.error_message = error_message
            sync_log.end_time = timezone.now()
            sync_log.save()
            
            return {"success": False, "message": error_message}
    
    @staticmethod
    def _parse_date(date_str):
        """Converte string de data para objeto date"""
        if not date_str:
            return None
        
        try:
            return datetime.strptime(date_str, '%d/%m/%Y').date()
        except ValueError:
            try:
                # Tentar formato alternativo
                return datetime.strptime(date_str, '%Y-%m-%d').date()
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
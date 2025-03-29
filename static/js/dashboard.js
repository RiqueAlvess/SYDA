// Modificações para melhorar o tratamento de erros em static/js/dashboard.js

document.addEventListener('DOMContentLoaded', function() {
    // Se CHART_CONFIG não estiver definido globalmente, define um valor padrão
    const chartConfig = (typeof window.CHART_CONFIG !== 'undefined') ? window.CHART_CONFIG : { displaylogo: false };

    // Configurações
    const CONFIG = {
        AVG_WORK_HOURS_PER_MONTH: 176,
        MIN_WAGE_BRAZIL: 1412,
        HOURLY_RATE: 1412 / 176,
        COLORS: [
            '#1565C0', '#2E7D32', '#F57C00', '#8E24AA', 
            '#D81B60', '#5E35B1', '#00ACC1', '#43A047',
            '#E53935', '#6D4C41', '#1E88E5', '#00897B'
        ]
    };

    // Estado global
    let state = {
        rawEmployees: [],
        rawAbsences: [],
        filteredAbsences: [],
        metrics: {},
        charts: {}
    };

    // Elementos DOM
    const DOM = {
        loading: document.getElementById('loading-overlay'),
        kpis: {
            rate: document.getElementById('absenteeism-rate'),
            totalCost: document.getElementById('total-cost'),
            daysOff: document.getElementById('total-days-off'),
            employeesVsAbsences: document.getElementById('employees-vs-absences'),
            hoursOff: document.getElementById('total-hours-off'),
            hourlyRate: document.getElementById('hourly-rate'),
            costValue: document.getElementById('total-cost-value'),
            costPercent: document.getElementById('total-cost-percent'),
            savings10: document.getElementById('savings-10'),
            savings20: document.getElementById('savings-20'),
            savings30: document.getElementById('savings-30')
        },
        filters: {
            startDate: document.getElementById('start-date'),
            endDate: document.getElementById('end-date'),
            unit: document.getElementById('unit-filter'),
            department: document.getElementById('department-filter'),
            situation: document.getElementById('situation-filter')
        },
        charts: {
            units: document.getElementById('units-chart'),
            departments: document.getElementById('departments-chart'),
            cid: document.getElementById('cid-chart'),
            months: document.getElementById('month-chart'),
            gender: document.getElementById('gender-chart'),
            costSector: document.getElementById('cost-chart')
        }
    };

    // Inicialização principal
    async function init() {
        try {
            console.log("Iniciando carregamento do dashboard...");
            console.log("DOM chart elements:", DOM.charts);
            
            showLoading();
            
            // Verificar se há elementos no DOM antes de tentar carregar dados
            if (!verifyDomElements()) {
                throw new Error('Elementos DOM necessários não foram encontrados');
            }
            
            await loadData();
            
            // Verificar se os dados foram carregados corretamente
            if (!state.rawEmployees.length || !state.rawAbsences.length) {
                throw new Error('Não foi possível carregar dados suficientes para o dashboard');
            }
            
            console.log("Dados carregados com sucesso. Aplicando filtros...");
            applyInitialFilters();
            
            console.log("Calculando métricas...");
            calculateMetrics();
            
            console.log("Atualizando KPIs...");
            updateKPIs();
            
            console.log("Renderizando gráficos...");
            renderCharts();
            
            console.log("Configurando listeners de eventos...");
            setupEventListeners();
            setupResizeListener();
            
            console.log("Dashboard inicializado com sucesso!");
        } catch (error) {
            console.error("Erro na inicialização do dashboard:", error);
            handleError(error);
        } finally {
            hideLoading();
        }
    }
    
    // Verifica se todos os elementos DOM necessários estão presentes
    function verifyDomElements() {
        // Verifica elementos dos gráficos
        for (const [key, element] of Object.entries(DOM.charts)) {
            if (!element) {
                console.error(`Elemento DOM não encontrado: charts.${key}`);
                return false;
            }
        }
        
        // Se chegamos aqui, tudo está OK (não precisamos verificar todos os elementos)
        return true;
    }

    // Carregamento dos dados via API
    async function loadData() {
        try {
            console.log("Buscando dados de API...");
            
            const employeesPromise = fetch('/employees/api/dashboard/employees/');
            const absencesPromise = fetch('/employees/api/dashboard/absences/');
            
            const [employeesRes, absencesRes] = await Promise.all([employeesPromise, absencesPromise]);
            
            console.log("Status das respostas:", {
                employees: employeesRes.status,
                absences: absencesRes.status
            });
            
            if (!employeesRes.ok) {
                const errorText = await employeesRes.text();
                console.error("Erro na API de funcionários:", errorText);
                throw new Error(`Falha ao carregar dados de funcionários (${employeesRes.status})`);
            }
            
            if (!absencesRes.ok) {
                const errorText = await absencesRes.text();
                console.error("Erro na API de absenteísmo:", errorText);
                throw new Error(`Falha ao carregar dados de absenteísmo (${absencesRes.status})`);
            }
            
            state.rawEmployees = await employeesRes.json();
            state.rawAbsences = await absencesRes.json();
            
            console.log("Dados carregados:", {
                employees: state.rawEmployees.length,
                absences: state.rawAbsences.length
            });
            
            if (!state.rawEmployees.length || !state.rawAbsences.length) {
                console.warn("Um ou mais conjuntos de dados estão vazios");
            }
        } catch (error) {
            console.error("Erro ao carregar dados:", error);
            throw new Error(`Erro ao carregar dados: ${error.message}`);
        }
    }

    // Aplicação dos filtros iniciais (datas)
    function applyInitialFilters() {
        if (!DOM.filters.startDate || !DOM.filters.endDate) {
            console.warn("Elementos de filtro de data não encontrados");
            state.filteredAbsences = [...state.rawAbsences];
            return;
        }
        
        if (!DOM.filters.startDate.value) {
            const threeMonthsAgo = new Date();
            threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
            DOM.filters.startDate.value = threeMonthsAgo.toISOString().slice(0, 10);
        }
        
        if (!DOM.filters.endDate.value) {
            const today = new Date();
            DOM.filters.endDate.value = today.toISOString().slice(0, 10);
        }
        
        try {
            const startDate = new Date(DOM.filters.startDate.value);
            const endDate = new Date(DOM.filters.endDate.value);
            
            state.filteredAbsences = state.rawAbsences.filter(absence => {
                if (!absence.dt_inicio_atestado) return false;
                const date = new Date(absence.dt_inicio_atestado);
                return date >= startDate && date <= endDate;
            });
            
            console.log("Absences filtradas por data:", {
                total: state.rawAbsences.length,
                filtered: state.filteredAbsences.length,
                startDate: DOM.filters.startDate.value,
                endDate: DOM.filters.endDate.value
            });
        } catch (error) {
            console.error("Erro ao aplicar filtros:", error);
            // Em caso de erro, não aplicamos filtros
            state.filteredAbsences = [...state.rawAbsences];
        }
    }

    // Cálculo das métricas
    function calculateMetrics() {
        try {
            const totalEmployees = state.rawEmployees.length;
            const totalAbsences = state.filteredAbsences.length;
            const totalDays = state.filteredAbsences.reduce((sum, a) => sum + (a.dias_afastados || 0), 0);
            const totalHours = totalDays * 8;
            const cost = totalHours * CONFIG.HOURLY_RATE;
            
            // Obter meses únicos, com fallback para 1 se não houver dados
            const months = new Set();
            state.filteredAbsences.forEach(a => {
                if (a.dt_inicio_atestado) {
                    months.add(a.dt_inicio_atestado.slice(0, 7));
                }
            });
            const uniqueMonths = months.size || 1;
            
            const rate = (totalDays / (22 * uniqueMonths * totalEmployees)) * 100;

            state.metrics = {
                totalEmployees,
                totalAbsences,
                totalDays,
                totalHours,
                cost,
                rate,
                costPercentage: (cost / (CONFIG.MIN_WAGE_BRAZIL * totalEmployees)) * 100
            };
            
            console.log("Métricas calculadas:", state.metrics);
        } catch (error) {
            console.error("Erro ao calcular métricas:", error);
            state.metrics = {
                totalEmployees: 0,
                totalAbsences: 0,
                totalDays: 0,
                totalHours: 0,
                cost: 0,
                rate: 0,
                costPercentage: 0
            };
        }
    }

    // Renderização dos gráficos
    function renderCharts() {
        try {
            console.log("Preparando dados para gráficos...");
            prepareChartData();
            
            console.log("Renderizando gráficos individuais...");
            renderBarChart('units', 'Unidades', ['Dias', 'Atestados']);
            renderBarChart('departments', 'Setores', ['Dias', 'Atestados']);
            renderBarChart('cid', 'CIDs', ['Atestados', 'Dias']);
            renderLineChart();
            renderPieChart();
            renderCostChart();
            
            console.log("Todos os gráficos renderizados com sucesso!");
        } catch (error) {
            console.error("Erro na renderização dos gráficos:", error);
            showToast("Erro nos gráficos", `Não foi possível renderizar alguns gráficos: ${error.message}`, "warning");
        }
    }

    // Preparação dos dados para os gráficos
    function prepareChartData() {
        try {
            state.charts = {
                units: groupData('unidade', 'Dias', 'Atestados'),
                departments: groupData('setor', 'Dias', 'Atestados'),
                cid: groupData('grupo_patologico', 'Atestados', 'Dias'),
                months: groupMonthlyData(),
                gender: groupGenderData(),
                costSector: groupCostData()
            };
            
            console.log("Dados de gráficos preparados:", {
                units: state.charts.units.length,
                departments: state.charts.departments.length,
                cid: state.charts.cid.length,
                months: state.charts.months.length,
                gender: state.charts.gender.length,
                costSector: state.charts.costSector.length
            });
        } catch (error) {
            console.error("Erro ao preparar dados de gráficos:", error);
            throw error;
        }
    }

    // Função genérica para agrupar dados por campo
    function groupData(field, primaryLabel, secondaryLabel) {
        try {
            const groups = {};
            state.filteredAbsences.forEach(a => {
                const fieldValue = a[field];
                const key = fieldValue || 'Não informado';
                
                if (!groups[key]) {
                    groups[key] = { primary: 0, secondary: 0 };
                }
                
                groups[key].primary += a.dias_afastados || 0;
                groups[key].secondary++;
            });

            return Object.entries(groups)
                .sort((a, b) => b[1].primary - a[1].primary)
                .slice(0, 10)
                .map(([label, data]) => ({
                    label,
                    [primaryLabel]: data.primary,
                    [secondaryLabel]: data.secondary
                }));
        } catch (error) {
            console.error(`Erro ao agrupar dados por ${field}:`, error);
            return [];
        }
    }

    // Agrupamento dos dados mensais
    function groupMonthlyData() {
        try {
            const months = {};
            state.filteredAbsences.forEach(a => {
                if (!a.dt_inicio_atestado) return;
                
                const month = a.dt_inicio_atestado.slice(0, 7);
                if (!months[month]) {
                    months[month] = { dias: 0, atestados: 0 };
                }
                
                months[month].dias += a.dias_afastados || 0;
                months[month].atestados++;
            });

            return Object.entries(months)
                .sort(([a], [b]) => a.localeCompare(b))
                .map(([month, data]) => ({
                    month: formatMonth(month),
                    Dias: data.dias,
                    Atestados: data.atestados
                }));
        } catch (error) {
            console.error("Erro ao agrupar dados mensais:", error);
            return [];
        }
    }

    // Agrupamento dos dados por gênero (para gráfico de pizza)
    function groupGenderData() {
        try {
            const genderMap = { '1': 'Masculino', '2': 'Feminino' };
            const counts = state.filteredAbsences.reduce((acc, a) => {
                const gender = genderMap[a.sexo] || 'Não informado';
                acc[gender] = (acc[gender] || 0) + 1;
                return acc;
            }, {});
            
            return Object.entries(counts).map(([label, value]) => ({
                label,
                value
            }));
        } catch (error) {
            console.error("Erro ao agrupar dados por gênero:", error);
            return [];
        }
    }

    // Agrupamento dos dados de custo por setor
    function groupCostData() {
        try {
            const sectorCosts = {};
            state.filteredAbsences.forEach(a => {
                const sector = a.setor || 'Não informado';
                if (!sectorCosts[sector]) {
                    sectorCosts[sector] = { days: 0 };
                }
                sectorCosts[sector].days += a.dias_afastados || 0;
            });
            
            return Object.entries(sectorCosts)
                .sort((a, b) => b[1].days - a[1].days)
                .slice(0, 5)
                .map(([label, data]) => ({
                    label,
                    Custo: (data.days * 8) * CONFIG.HOURLY_RATE
                }));
        } catch (error) {
            console.error("Erro ao agrupar dados de custo:", error);
            return [];
        }
    }

    function renderBarChart(chartKey, title, series) {
        try {
            const data = state.charts[chartKey];
            if (!data || !data.length) {
                console.log(`Sem dados para o gráfico ${chartKey}`);
                return;
            }
            
            const chartElement = DOM.charts[chartKey];
            if (!chartElement) {
                console.error(`Elemento de gráfico não encontrado para ${chartKey}`);
                return;
            }
            
            const traces = series.map((s, i) => ({
                x: data.map(d => d.label),
                y: data.map(d => d[s]),
                name: s,
                type: 'bar',
                marker: { color: CONFIG.COLORS[i] }
            }));

            Plotly.newPlot(chartElement, traces, {
                title: `Top 10 ${title}`,
                barmode: 'group',
                height: 400
            }, chartConfig);
            
            console.log(`Gráfico de barras renderizado: ${chartKey}`);
        } catch (error) {
            console.error(`Erro ao renderizar gráfico de barras ${chartKey}:`, error);
            const chartElement = DOM.charts[chartKey];
            if (chartElement) {
                chartElement.innerHTML = `<div class="text-center p-4">
                    <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 2rem;"></i>
                    <p>Não foi possível renderizar este gráfico.</p>
                </div>`;
            }
        }
    }

    function renderLineChart() {
        try {
            const data = state.charts.months;
            if (!data || !data.length) {
                console.log("Sem dados para o gráfico de meses");
                return;
            }
            
            const chartElement = DOM.charts.months;
            if (!chartElement) {
                console.error("Elemento de gráfico para meses não encontrado");
                return;
            }
            
            const trace1 = {
                x: data.map(d => d.month),
                y: data.map(d => d.Dias),
                name: 'Dias Afastados',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: CONFIG.COLORS[0] }
            };

            const trace2 = {
                x: data.map(d => d.month),
                y: data.map(d => d.Atestados),
                name: 'Atestados',
                type: 'scatter',
                mode: 'lines+markers',
                line: { color: CONFIG.COLORS[1], dash: 'dot' }
            };

            Plotly.newPlot(chartElement, [trace1, trace2], {
                title: 'Evolução Mensal',
                height: 400
            }, chartConfig);
            
            console.log("Gráfico de linha renderizado");
        } catch (error) {
            console.error("Erro ao renderizar gráfico de linha:", error);
            const chartElement = DOM.charts.months;
            if (chartElement) {
                chartElement.innerHTML = `<div class="text-center p-4">
                    <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 2rem;"></i>
                    <p>Não foi possível renderizar este gráfico.</p>
                </div>`;
            }
        }
    }

    function renderPieChart() {
        try {
            const data = state.charts.gender;
            if (!data || !data.length) {
                console.log("Sem dados para o gráfico de gênero");
                return;
            }
            
            const chartElement = DOM.charts.gender;
            if (!chartElement) {
                console.error("Elemento de gráfico para gênero não encontrado");
                return;
            }
            
            Plotly.newPlot(chartElement, [{
                values: data.map(d => d.value),
                labels: data.map(d => d.label),
                type: 'pie',
                hole: 0.4,
                marker: { colors: CONFIG.COLORS }
            }], {
                title: 'Distribuição por Gênero',
                height: 400
            }, chartConfig);
            
            console.log("Gráfico de pizza renderizado");
        } catch (error) {
            console.error("Erro ao renderizar gráfico de pizza:", error);
            const chartElement = DOM.charts.gender;
            if (chartElement) {
                chartElement.innerHTML = `<div class="text-center p-4">
                    <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 2rem;"></i>
                    <p>Não foi possível renderizar este gráfico.</p>
                </div>`;
            }
        }
    }

    function renderCostChart() {
        try {
            const data = state.charts.costSector;
            if (!data || !data.length) {
                console.log("Sem dados para o gráfico de custos");
                return;
            }
            
            const chartElement = DOM.charts.costSector;
            if (!chartElement) {
                console.error("Elemento de gráfico para custos não encontrado");
                return;
            }
            
            Plotly.newPlot(chartElement, [{
                x: data.map(d => d.label),
                y: data.map(d => d.Custo),
                type: 'bar',
                marker: { color: CONFIG.COLORS[11] }
            }], {
                title: 'Custo por Setor',
                yaxis: { tickprefix: 'R$ ' },
                height: 400
            }, chartConfig);
            
            console.log("Gráfico de custos renderizado");
        } catch (error) {
            console.error("Erro ao renderizar gráfico de custos:", error);
            const chartElement = DOM.charts.costSector;
            if (chartElement) {
                chartElement.innerHTML = `<div class="text-center p-4">
                    <i class="fas fa-exclamation-triangle text-warning mb-3" style="font-size: 2rem;"></i>
                    <p>Não foi possível renderizar este gráfico.</p>
                </div>`;
            }
        }
    }

    // Helper para formatar mês
    function formatMonth(monthString) {
        try {
            const [year, month] = monthString.split('-');
            return `${month}/${year}`;
        } catch (error) {
            console.error("Erro ao formatar mês:", error);
            return monthString || 'N/A';
        }
    }

    // Helper para formatar moeda
    function formatCurrency(value) {
        try {
            return new Intl.NumberFormat('pt-BR', { 
                style: 'currency', 
                currency: 'BRL' 
            }).format(value);
        } catch (error) {
            console.error("Erro ao formatar moeda:", error);
            return `R$ ${value.toFixed(2)}`.replace('.', ',');
        }
    }

    // Atualização dos KPIs na interface
    function updateKPIs() {
        try {
            // Verificar se cada elemento existe antes de atualizá-lo
            if (DOM.kpis.rate) DOM.kpis.rate.textContent = `${state.metrics.rate.toFixed(2)}%`;
            if (DOM.kpis.totalCost) DOM.kpis.totalCost.textContent = formatCurrency(state.metrics.cost);
            if (DOM.kpis.daysOff) DOM.kpis.daysOff.textContent = state.metrics.totalDays;
            if (DOM.kpis.employeesVsAbsences) DOM.kpis.employeesVsAbsences.textContent = `${state.metrics.totalEmployees} / ${state.metrics.totalAbsences}`;
            if (DOM.kpis.hoursOff) DOM.kpis.hoursOff.textContent = `${state.metrics.totalHours} horas`;
            if (DOM.kpis.hourlyRate) DOM.kpis.hourlyRate.textContent = formatCurrency(CONFIG.HOURLY_RATE);
            if (DOM.kpis.costValue) DOM.kpis.costValue.textContent = formatCurrency(state.metrics.cost);
            
            if (DOM.kpis.costPercent && state.metrics.costPercentage) {
                DOM.kpis.costPercent.textContent = `Representa ${state.metrics.costPercentage.toFixed(2)}% da folha`;
            }
            
            if (DOM.kpis.savings10) DOM.kpis.savings10.textContent = formatCurrency(state.metrics.cost * 0.1);
            if (DOM.kpis.savings20) DOM.kpis.savings20.textContent = formatCurrency(state.metrics.cost * 0.2);
            if (DOM.kpis.savings30) DOM.kpis.savings30.textContent = formatCurrency(state.metrics.cost * 0.3);
            
            console.log("KPIs atualizados");
        } catch (error) {
            console.error("Erro ao atualizar KPIs:", error);
        }
    }

    // Configuração dos listeners de eventos para filtros
    function setupEventListeners() {
        try {
            if (DOM.filters.startDate) DOM.filters.startDate.addEventListener('change', handleFilterChange);
            if (DOM.filters.endDate) DOM.filters.endDate.addEventListener('change', handleFilterChange);
            if (DOM.filters.unit) DOM.filters.unit.addEventListener('change', handleFilterChange);
            if (DOM.filters.department) DOM.filters.department.addEventListener('change', handleFilterChange);
            if (DOM.filters.situation) DOM.filters.situation.addEventListener('change', handleFilterChange);
            
            console.log("Event listeners configurados");
        } catch (error) {
            console.error("Erro ao configurar event listeners:", error);
        }
    }

    async function handleFilterChange() {
        try {
            showLoading();
            applyInitialFilters();
            calculateMetrics();
            updateKPIs();
            renderCharts();
        } catch (error) {
            console.error("Erro ao aplicar filtros:", error);
            handleError(error);
        } finally {
            hideLoading();
        }
    }

    // Listener para redimensionamento (responsividade dos gráficos)
    function setupResizeListener() {
        try {
            window.addEventListener('resize', function() {
                Object.values(DOM.charts).forEach(chart => {
                    if (chart) Plotly.Plots.resize(chart);
                });
            });
        } catch (error) {
            console.error("Erro ao configurar listener de resize:", error);
        }
    }

    // Utilitários de interface
    function showLoading() {
        if (DOM.loading) DOM.loading.style.display = 'flex';
    }

    function hideLoading() {
        if (DOM.loading) DOM.loading.style.display = 'none';
    }

    function handleError(error) {
        console.error('Erro crítico:', error);
        
        // Esconder o loading indicator
        hideLoading();
        
        // Mostrar uma mensagem de erro
        const errorMsg = `Erro ao carregar o dashboard: ${error.message}`;
        alert(errorMsg);
        
        try {
            // Tentar mostrar um toast
            showToast("Erro", errorMsg, "danger");
        } catch (e) {
            console.error("Erro ao mostrar toast:", e);
        }
    }
    
    // Função para mostrar toast (notificação)
    function showToast(title, message, type = 'success') {
        try {
            const toastEl = document.getElementById('notification-toast');
            if (!toastEl) return;
            
            const toastTitle = document.getElementById('toast-title');
            const toastMessage = document.getElementById('toast-message');
            
            if (toastTitle) toastTitle.textContent = title;
            if (toastMessage) toastMessage.innerHTML = message;
            
            toastEl.className = `toast text-white bg-${type}`;
            
            const toast = new bootstrap.Toast(toastEl, {
                autohide: true,
                delay: 5000
            });
            toast.show();
        } catch (error) {
            console.error("Erro ao mostrar toast:", error);
        }
    }

    // Inicia a aplicação
    console.log("Iniciando dashboard.js...");
    init();
});

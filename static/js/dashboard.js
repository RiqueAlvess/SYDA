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
            console.log("DOM chart elements:", DOM.charts);
            showLoading();
            await loadData();
            applyInitialFilters();
            calculateMetrics();
            updateKPIs();
            renderCharts();
            setupEventListeners();
            setupResizeListener();
        } catch (error) {
            handleError(error);
        } finally {
            hideLoading();
        }
    }

    // Carregamento dos dados via API
    async function loadData() {
        const [employeesRes, absencesRes] = await Promise.all([
            fetch('/employees/api/dashboard/employees/'),
            fetch('/employees/api/dashboard/absences/')
        ]);
        
        if (!employeesRes.ok || !absencesRes.ok) throw new Error('Falha ao carregar dados');
        
        state.rawEmployees = await employeesRes.json();
        state.rawAbsences = await absencesRes.json();
        
        console.log("Loaded data:", {
            employees: state.rawEmployees.length,
            absences: state.rawAbsences.length
        });
        
        if (!state.rawEmployees.length || !state.rawAbsences.length) {
            throw new Error('Dados insuficientes');
        }
    }

    // Aplicação dos filtros iniciais (datas)
    function applyInitialFilters() {
        if (!DOM.filters.startDate.value) {
            const threeMonthsAgo = new Date();
            threeMonthsAgo.setMonth(threeMonthsAgo.getMonth() - 3);
            DOM.filters.startDate.value = threeMonthsAgo.toISOString().slice(0, 10);
        }
        
        if (!DOM.filters.endDate.value) {
            const today = new Date();
            DOM.filters.endDate.value = today.toISOString().slice(0, 10);
        }
        
        state.filteredAbsences = state.rawAbsences.filter(absence => {
            if (!absence.dt_inicio_atestado) return false;
            const date = new Date(absence.dt_inicio_atestado);
            return date >= new Date(DOM.filters.startDate.value) &&
                   date <= new Date(DOM.filters.endDate.value);
        });
        
        console.log("Filtered absences:", state.filteredAbsences.length);
    }

    // Cálculo das métricas
    function calculateMetrics() {
        const totalEmployees = state.rawEmployees.length;
        const totalAbsences = state.filteredAbsences.length;
        const totalDays = state.filteredAbsences.reduce((sum, a) => sum + (a.dias_afastados || 0), 0);
        const totalHours = totalDays * 8;
        const cost = totalHours * CONFIG.HOURLY_RATE;
        const months = new Set(state.filteredAbsences.map(a => a.dt_inicio_atestado?.slice(0, 7))).size || 1;
        const rate = (totalDays / (22 * months * totalEmployees)) * 100;

        state.metrics = {
            totalEmployees,
            totalAbsences,
            totalDays,
            totalHours,
            cost,
            rate,
            costPercentage: (cost / (CONFIG.MIN_WAGE_BRAZIL * totalEmployees)) * 100
        };
        
        console.log("Calculated metrics:", state.metrics);
    }

    // Preparação dos dados para os gráficos
    function prepareChartData() {
        state.charts = {
            units: groupData('unidade', 'Dias', 'Atestados'),
            departments: groupData('setor', 'Dias', 'Atestados'),
            cid: groupData('grupo_patologico', 'Atestados', 'Dias'),
            months: groupMonthlyData(),
            gender: groupGenderData(),
            costSector: groupCostData()
        };
        
        console.log("Chart data prepared:", {
            units: state.charts.units.length,
            departments: state.charts.departments.length,
            cid: state.charts.cid.length,
            months: state.charts.months.length,
            gender: state.charts.gender.length,
            costSector: state.charts.costSector.length
        });
    }

    // Função genérica para agrupar dados por campo
    function groupData(field, primaryLabel, secondaryLabel) {
        const groups = {};
        state.filteredAbsences.forEach(a => {
            const key = a[field] || 'Não informado';
            groups[key] = groups[key] || { primary: 0, secondary: 0 };
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
    }

    // Agrupamento dos dados mensais
    function groupMonthlyData() {
        const months = {};
        state.filteredAbsences.forEach(a => {
            if (!a.dt_inicio_atestado) return;
            const month = a.dt_inicio_atestado.slice(0, 7);
            months[month] = months[month] || { dias: 0, atestados: 0 };
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
    }

    // Agrupamento dos dados por gênero (para gráfico de pizza)
    function groupGenderData() {
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
    }

    // Agrupamento dos dados de custo por setor
    function groupCostData() {
        const sectorCosts = {};
        state.filteredAbsences.forEach(a => {
            const sector = a.setor || 'Não informado';
            sectorCosts[sector] = sectorCosts[sector] || { days: 0 };
            sectorCosts[sector].days += a.dias_afastados || 0;
        });
        
        return Object.entries(sectorCosts)
            .sort((a, b) => b[1].days - a[1].days)
            .slice(0, 5)
            .map(([label, data]) => ({
                label,
                Custo: (data.days * 8) * CONFIG.HOURLY_RATE
            }));
    }

    // Renderização dos gráficos
    function renderCharts() {
        prepareChartData();
        renderBarChart('units', 'Unidades', ['Dias', 'Atestados']);
        renderBarChart('departments', 'Setores', ['Dias', 'Atestados']);
        renderBarChart('cid', 'CIDs', ['Atestados', 'Dias']);
        renderLineChart();
        renderPieChart();
        renderCostChart();
    }

    function renderBarChart(chartKey, title, series) {
        const data = state.charts[chartKey];
        if (!data || !data.length) {
            console.log(`No data for ${chartKey} chart`);
            return;
        }
        
        const chartElement = DOM.charts[chartKey];
        if (!chartElement) {
            console.error(`Chart element not found for ${chartKey}`);
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
        
        console.log(`Rendered bar chart: ${chartKey}`);
    }

    function renderLineChart() {
        const data = state.charts.months;
        if (!data || !data.length) {
            console.log("No data for months chart");
            return;
        }
        
        const chartElement = DOM.charts.months;
        if (!chartElement) {
            console.error("Months chart element not found");
            return;
        }
        
        const trace1 = {
            x: data.map(d => d.month),
            y: data.map(d => d.Dias),
            name: 'Dias Afastados',
            line: { color: CONFIG.COLORS[0] }
        };

        const trace2 = {
            x: data.map(d => d.month),
            y: data.map(d => d.Atestados),
            name: 'Atestados',
            line: { color: CONFIG.COLORS[1], dash: 'dot' }
        };

        Plotly.newPlot(chartElement, [trace1, trace2], {
            title: 'Evolução Mensal',
            height: 400
        }, chartConfig);
        
        console.log("Rendered line chart");
    }

    function renderPieChart() {
        const data = state.charts.gender;
        if (!data || !data.length) {
            console.log("No data for gender chart");
            return;
        }
        
        const chartElement = DOM.charts.gender;
        if (!chartElement) {
            console.error("Gender chart element not found");
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
        
        console.log("Rendered pie chart");
    }

    function renderCostChart() {
        const data = state.charts.costSector;
        if (!data || !data.length) {
            console.log("No data for cost chart");
            return;
        }
        
        const chartElement = DOM.charts.costSector;
        if (!chartElement) {
            console.error("Cost chart element not found");
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
        
        console.log("Rendered cost chart");
    }

    // Helper para formatar mês
    function formatMonth(monthString) {
        const [year, month] = monthString.split('-');
        return `${month}/${year}`;
    }

    // Helper para formatar moeda
    function formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', { 
            style: 'currency', 
            currency: 'BRL' 
        }).format(value);
    }

    // Atualização dos KPIs na interface
    function updateKPIs() {
        if (DOM.kpis.rate) DOM.kpis.rate.textContent = `${state.metrics.rate.toFixed(2)}%`;
        if (DOM.kpis.totalCost) DOM.kpis.totalCost.textContent = formatCurrency(state.metrics.cost);
        if (DOM.kpis.daysOff) DOM.kpis.daysOff.textContent = state.metrics.totalDays;
        if (DOM.kpis.employeesVsAbsences) DOM.kpis.employeesVsAbsences.textContent = 
            `${state.metrics.totalEmployees} / ${state.metrics.totalAbsences}`;
        if (DOM.kpis.hoursOff) DOM.kpis.hoursOff.textContent = `${state.metrics.totalHours} horas`;
        if (DOM.kpis.hourlyRate) DOM.kpis.hourlyRate.textContent = formatCurrency(CONFIG.HOURLY_RATE);
        if (DOM.kpis.costValue) DOM.kpis.costValue.textContent = formatCurrency(state.metrics.cost);
        if (DOM.kpis.costPercent && state.metrics.costPercentage) DOM.kpis.costPercent.textContent = 
            `Representa ${state.metrics.costPercentage.toFixed(2)}% da folha`;
        if (DOM.kpis.savings10) DOM.kpis.savings10.textContent = formatCurrency(state.metrics.cost * 0.1);
        if (DOM.kpis.savings20) DOM.kpis.savings20.textContent = formatCurrency(state.metrics.cost * 0.2);
        if (DOM.kpis.savings30) DOM.kpis.savings30.textContent = formatCurrency(state.metrics.cost * 0.3);
        
        console.log("KPIs updated");
    }

    // Configuração dos listeners de eventos para filtros
    function setupEventListeners() {
        if (DOM.filters.startDate) DOM.filters.startDate.addEventListener('change', handleFilterChange);
        if (DOM.filters.endDate) DOM.filters.endDate.addEventListener('change', handleFilterChange);
        if (DOM.filters.unit) DOM.filters.unit.addEventListener('change', handleFilterChange);
        if (DOM.filters.department) DOM.filters.department.addEventListener('change', handleFilterChange);
        if (DOM.filters.situation) DOM.filters.situation.addEventListener('change', handleFilterChange);
        
        console.log("Event listeners set up");
    }

    async function handleFilterChange() {
        try {
            showLoading();
            applyInitialFilters();
            calculateMetrics();
            updateKPIs();
            renderCharts();
        } catch (error) {
            handleError(error);
        } finally {
            hideLoading();
        }
    }

    // Listener para redimensionamento (responsividade dos gráficos)
    function setupResizeListener() {
        window.addEventListener('resize', function() {
            Object.values(DOM.charts).forEach(chart => {
                if (chart) Plotly.Plots.resize(chart);
            });
        });
    }

    // Utilitários de interface
    function showLoading() {
        if (DOM.loading) DOM.loading.style.display = 'flex';
    }

    function hideLoading() {
        if (DOM.loading) DOM.loading.style.display = 'none';
    }

    function handleError(error) {
        console.error('Erro:', error);
        alert(`Erro crítico: ${error.message}`);
    }

    // Inicia a aplicação
    init();
});

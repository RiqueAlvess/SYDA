// static/js/dashboard.js
document.addEventListener('DOMContentLoaded', function() {
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
            units: document.getElementById('chart-units'),
            departments: document.getElementById('chart-departments'),
            cid: document.getElementById('chart-cid'),
            months: document.getElementById('chart-month'),
            gender: document.getElementById('chart-gender'),
            costSector: document.getElementById('chart-cost-sector')
        }
    };

    // Main initialization
    async function init() {
        try {
            showLoading();
            await loadData();
            applyInitialFilters();
            calculateMetrics();
            updateKPIs();
            renderCharts();
            setupEventListeners();
        } catch (error) {
            handleError(error);
        } finally {
            hideLoading();
        }
    }

    // Data loading
    async function loadData() {
        const [employeesRes, absencesRes] = await Promise.all([
            fetch('/employees/api/dashboard/employees/'),
            fetch('/employees/api/dashboard/absences/')
        ]);
        
        if (!employeesRes.ok || !absencesRes.ok) throw new Error('Falha ao carregar dados');
        
        state.rawEmployees = await employeesRes.json();
        state.rawAbsences = await absencesRes.json();
        
        if (!state.rawEmployees.length || !state.rawAbsences.length) {
            throw new Error('Dados insuficientes');
        }
    }

    // Filter logic
    function applyInitialFilters() {
        state.filteredAbsences = state.rawAbsences.filter(absence => {
            const date = new Date(absence.dt_inicio_atestado);
            return date >= new Date(DOM.filters.startDate.value) && 
                   date <= new Date(DOM.filters.endDate.value);
        });
    }

    // Metrics calculation
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
    }

    // Charts data preparation
    function prepareChartData() {
        state.charts = {
            units: groupData('nome_unidade', 'Dias', 'Atestados'),
            departments: groupData('nome_setor', 'Dias', 'Atestados'),
            cid: groupData('grupo_patologico', 'Atestados', 'Dias'),
            months: groupMonthlyData(),
            gender: groupGenderData(),
            costSector: groupCostData()
        };
    }

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

    function groupCostData() {
        return state.charts.departments.slice(0, 5).map(dept => ({
            label: dept.label,
            Custo: (dept.Dias * 8) * CONFIG.HOURLY_RATE
        }));
    }

    // Charts rendering
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
        const traces = series.map((s, i) => ({
            x: data.map(d => d.label),
            y: data.map(d => d[s]),
            name: s,
            type: 'bar',
            marker: { color: CONFIG.COLORS[i] }
        }));

        Plotly.newPlot(DOM.charts[chartKey], traces, {
            title: `Top 10 ${title}`,
            barmode: 'group',
            height: 400
        });
    }

    function renderLineChart() {
        const data = state.charts.months;
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

        Plotly.newPlot(DOM.charts.months, [trace1, trace2], {
            title: 'Evolução Mensal',
            height: 400
        });
    }

    function renderPieChart() {
        const data = state.charts.gender;
        Plotly.newPlot(DOM.charts.gender, [{
            values: data.map(d => d.value),
            labels: data.map(d => d.label),
            type: 'pie',
            hole: 0.4,
            marker: { colors: CONFIG.COLORS }
        }], {
            title: 'Distribuição por Gênero',
            height: 400
        });
    }

    function renderCostChart() {
        const data = state.charts.costSector;
        Plotly.newPlot(DOM.charts.costSector, [{
            x: data.map(d => d.label),
            y: data.map(d => d.Custo),
            type: 'bar',
            marker: { color: CONFIG.COLORS[11] }
        }], {
            title: 'Custo por Setor',
            yaxis: { tickprefix: 'R$ ' },
            height: 400
        });
    }

    // Helpers
    function formatMonth(monthString) {
        const [year, month] = monthString.split('-');
        return `${month}/${year}`;
    }

    function formatCurrency(value) {
        return new Intl.NumberFormat('pt-BR', { 
            style: 'currency', 
            currency: 'BRL' 
        }).format(value);
    }

    function updateKPIs() {
        DOM.kpis.rate.textContent = `${state.metrics.rate.toFixed(2)}%`;
        DOM.kpis.totalCost.textContent = formatCurrency(state.metrics.cost);
        DOM.kpis.daysOff.textContent = state.metrics.totalDays;
        DOM.kpis.employeesVsAbsences.textContent = 
            `${state.metrics.totalEmployees} / ${state.metrics.totalAbsences}`;
        DOM.kpis.hoursOff.textContent = `${state.metrics.totalHours} horas`;
        DOM.kpis.hourlyRate.textContent = formatCurrency(CONFIG.HOURLY_RATE);
        DOM.kpis.costValue.textContent = formatCurrency(state.metrics.cost);
        DOM.kpis.costPercent.textContent = 
            `Representa ${state.metrics.costPercentage.toFixed(2)}% da folha`;
        DOM.kpis.savings10.textContent = formatCurrency(state.metrics.cost * 0.1);
        DOM.kpis.savings20.textContent = formatCurrency(state.metrics.cost * 0.2);
        DOM.kpis.savings30.textContent = formatCurrency(state.metrics.cost * 0.3);
    }

    // Event handling
    function setupEventListeners() {
        DOM.filters.startDate.addEventListener('change', handleFilterChange);
        DOM.filters.endDate.addEventListener('change', handleFilterChange);
        DOM.filters.unit.addEventListener('change', handleFilterChange);
        DOM.filters.department.addEventListener('change', handleFilterChange);
        DOM.filters.situation.addEventListener('change', handleFilterChange);
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

    // UI Utilities
    function showLoading() {
        DOM.loading.style.display = 'flex';
    }

    function hideLoading() {
        DOM.loading.style.display = 'none';
    }

    function handleError(error) {
        console.error('Erro:', error);
        alert(`Erro crítico: ${error.message}`);
    }

    // Start
    init();
});
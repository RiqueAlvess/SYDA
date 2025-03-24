document.addEventListener('DOMContentLoaded', function() {
    // Constantes e Configurações
    const AVG_WORK_HOURS_PER_MONTH = 8 * 22; // 8 horas por dia, 22 dias úteis por mês
    const MIN_WAGE_BRAZIL = 1412; // Valor do salário mínimo em 2024
    const HOURLY_RATE = MIN_WAGE_BRAZIL / AVG_WORK_HOURS_PER_MONTH;
    
    // Colors for charts
    const COLORS = [
        '#1565C0', '#2E7D32', '#F57C00', '#8E24AA', 
        '#D81B60', '#5E35B1', '#00ACC1', '#43A047',
        '#E53935', '#6D4C41', '#1E88E5', '#00897B'
    ];
    
    // Dados globais
    let originalData = {
        employees: [],
        absences: []
    };
    let filteredData = null;
    
    // Referências a filtros
    const startDateFilter = document.getElementById('start-date');
    const endDateFilter = document.getElementById('end-date');
    const unitFilter = document.getElementById('unit-filter');
    const departmentFilter = document.getElementById('department-filter');
    const situationFilter = document.getElementById('situation-filter');
    const resetFiltersBtn = document.getElementById('reset-filters');
    
    // Referências a elementos de exibição
    const absenteeismRateEl = document.getElementById('absenteeism-rate');
    const totalCostEl = document.getElementById('total-cost');
    const totalDaysOffEl = document.getElementById('total-days-off');
    const employeeVsAbsencesEl = document.getElementById('employees-vs-absences');
    const activeFiltersEl = document.getElementById('active-filters');
    const filteredRecordsEl = document.getElementById('filtered-records');
    const totalHoursOffEl = document.getElementById('total-hours-off');
    const hourlyRateEl = document.getElementById('hourly-rate');
    const totalCostValueEl = document.getElementById('total-cost-value');
    const totalCostPercentEl = document.getElementById('total-cost-percent');
    const savings10El = document.getElementById('savings-10');
    const savings20El = document.getElementById('savings-20');
    const savings30El = document.getElementById('savings-30');
    
    // Charts references
    let unitChart, departmentChart, cidChart, monthChart, genderChart, costSectorChart;
    
    // Loading overlay
    const loadingOverlay = document.getElementById('loading-overlay');
    
    // Set hourly rate display
    hourlyRateEl.textContent = formatCurrency(HOURLY_RATE);
    
    // Initialize dashboard
    initDashboard();
    
    // Add event listeners
    resetFiltersBtn.addEventListener('click', resetFilters);
    startDateFilter.addEventListener('change', applyFilters);
    endDateFilter.addEventListener('change', applyFilters);
    unitFilter.addEventListener('change', applyFilters);
    departmentFilter.addEventListener('change', applyFilters);
    situationFilter.addEventListener('change', applyFilters);
    
    // Initialize the dashboard
    function initDashboard() {
        showLoading();
        initCharts();
        loadData();
    }
    
    // Initialize empty charts
    function initCharts() {
        // Units Chart
        const unitChartCtx = document.getElementById('chart-units').getContext('2d');
        unitChart = new Chart(unitChartCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Dias Afastados',
                        data: [],
                        backgroundColor: COLORS[0],
                        borderColor: COLORS[0],
                        borderWidth: 1
                    },
                    {
                        label: 'Número de Atestados',
                        data: [],
                        backgroundColor: COLORS[1],
                        borderColor: COLORS[1],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Departments Chart
        const departmentChartCtx = document.getElementById('chart-departments').getContext('2d');
        departmentChart = new Chart(departmentChartCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Dias Afastados',
                        data: [],
                        backgroundColor: COLORS[2],
                        borderColor: COLORS[2],
                        borderWidth: 1
                    },
                    {
                        label: 'Número de Atestados',
                        data: [],
                        backgroundColor: COLORS[3],
                        borderColor: COLORS[3],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // CID Chart
        const cidChartCtx = document.getElementById('chart-cid').getContext('2d');
        cidChart = new Chart(cidChartCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Número de Atestados',
                        data: [],
                        backgroundColor: COLORS[4],
                        borderColor: COLORS[4],
                        borderWidth: 1
                    },
                    {
                        label: 'Dias Afastados',
                        data: [],
                        backgroundColor: COLORS[5],
                        borderColor: COLORS[5],
                        borderWidth: 1
                    }
                ]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    x: {
                        beginAtZero: true
                    }
                }
            }
        });
        
        // Month Chart
        const monthChartCtx = document.getElementById('chart-month').getContext('2d');
        monthChart = new Chart(monthChartCtx, {
            type: 'line',
            data: {
                labels: [],
                datasets: [
                    {
                        label: 'Dias Afastados',
                        data: [],
                        backgroundColor: 'rgba(136, 132, 216, 0.2)',
                        borderColor: COLORS[6],
                        borderWidth: 2,
                        tension: 0.2,
                        yAxisID: 'y'
                    },
                    {
                        label: 'Número de Atestados',
                        data: [],
                        backgroundColor: 'rgba(130, 202, 157, 0.2)',
                        borderColor: COLORS[7],
                        borderWidth: 2,
                        tension: 0.2,
                        yAxisID: 'y1'
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        position: 'left',
                        title: {
                            display: true,
                            text: 'Dias Afastados'
                        }
                    },
                    y1: {
                        beginAtZero: true,
                        position: 'right',
                        grid: {
                            drawOnChartArea: false
                        },
                        title: {
                            display: true,
                            text: 'Número de Atestados'
                        }
                    }
                }
            }
        });
        
        // Gender Chart
        const genderChartCtx = document.getElementById('chart-gender').getContext('2d');
        genderChart = new Chart(genderChartCtx, {
            type: 'pie',
            data: {
                labels: [],
                datasets: [{
                    data: [],
                    backgroundColor: [COLORS[8], COLORS[9], COLORS[10]],
                    borderColor: 'white',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom'
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.label}: ${context.raw} (${(context.parsed / context.dataset.data.reduce((a, b) => a + b, 0) * 100).toFixed(2)}%)`;
                            }
                        }
                    }
                }
            }
        });
        
        // Cost by Sector Chart
        const costSectorChartCtx = document.getElementById('chart-cost-sector').getContext('2d');
        costSectorChart = new Chart(costSectorChartCtx, {
            type: 'bar',
            data: {
                labels: [],
                datasets: [{
                    label: 'Custo (R$)',
                    data: [],
                    backgroundColor: COLORS[11],
                    borderColor: COLORS[11],
                    borderWidth: 1
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: {
                            callback: function(value) {
                                return formatCurrency(value).replace('R$ ', '');
                            }
                        }
                    }
                },
                plugins: {
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `Custo: ${formatCurrency(context.parsed.y)}`;
                            }
                        }
                    }
                }
            }
        });
    }
    
    // Load data from Django
    // Load data from Django
async function loadData() {
    try {
        showLoading();
        
        // Fetch employees and absences data
        console.log("Tentando buscar dados de funcionários...");
        const employeesResponse = await fetch('/employees/api/dashboard/employees/');
        
        if (!employeesResponse.ok) {
            console.error("Erro na resposta da API de funcionários:", employeesResponse.status);
            throw new Error(`Erro ao buscar dados de funcionários: ${employeesResponse.status}`);
        }
        
        console.log("Tentando buscar dados de absenteísmo...");
        const absencesResponse = await fetch('/employees/api/dashboard/absences/');
        
        if (!absencesResponse.ok) {
            console.error("Erro na resposta da API de absenteísmo:", absencesResponse.status);
            throw new Error(`Erro ao buscar dados de absenteísmo: ${absencesResponse.status}`);
        }
        
        const employeesData = await employeesResponse.json();
        const absencesData = await absencesResponse.json();
        
        console.log("Dados recebidos:", { 
            employees: employeesData.length, 
            absences: absencesData.length 
        });
        
        // Process data
        originalData = {
            employees: employeesData,
            absences: absencesData
        };
        
        // Fill filter options
        fillFilterOptions();
        
        // Apply initial filters
        applyFilters();
        
        hideLoading();
    } catch (error) {
        console.error('Erro ao carregar dados:', error);
        hideLoading();
        
        // Mostrar mensagem de erro mais amigável
        const container = document.querySelector('.container');
        const errorDiv = document.createElement('div');
        errorDiv.className = 'alert alert-danger my-4';
        errorDiv.innerHTML = `
            <h4 class="alert-heading">Erro ao carregar dados</h4>
            <p>${error.message || 'Não foi possível carregar os dados do dashboard.'}</p>
            <hr>
            <p class="mb-0">Tente acessar primeiro a página de <a href="/employees/">Funcionários</a> 
            e verificar se existem dados sincronizados.</p>
            <button class="btn btn-outline-danger mt-3" onclick="location.reload()">Tentar novamente</button>
        `;
        
        // Adicionar no início do container, após o header
        const dashboardHeader = document.querySelector('.dashboard-header');
        if (dashboardHeader && dashboardHeader.nextElementSibling) {
            container.insertBefore(errorDiv, dashboardHeader.nextElementSibling);
        } else {
            container.appendChild(errorDiv);
        }
    }
}
    
    // Fill filter options from data
    function fillFilterOptions() {
        // Reset select options
        unitFilter.innerHTML = '<option value="">Todas as Unidades</option>';
        departmentFilter.innerHTML = '<option value="">Todos os Setores</option>';
        situationFilter.innerHTML = '<option value="">Todas as Situações</option>';
        
        // Get unique values
        const units = _.uniq(originalData.absences.map(item => item.nome_unidade)).filter(Boolean).sort();
        const departments = _.uniq(originalData.absences.map(item => item.nome_setor)).filter(Boolean).sort();
        const situations = _.uniq(originalData.employees.map(item => item.situacao)).filter(Boolean).sort();
        
        // Find min and max dates for filters
        const dates = originalData.absences
            .filter(item => item.dt_inicio_atestado)
            .map(item => new Date(item.dt_inicio_atestado));
        
        if (dates.length > 0) {
            const minDate = new Date(Math.min(...dates));
            const maxDate = new Date(Math.max(...dates));
            
            startDateFilter.value = formatDateForInput(minDate);
            endDateFilter.value = formatDateForInput(maxDate);
        }
        
        // Add options to selects
        units.forEach(unit => {
            const option = document.createElement('option');
            option.value = unit;
            option.textContent = unit;
            unitFilter.appendChild(option);
        });
        
        departments.forEach(department => {
            const option = document.createElement('option');
            option.value = department;
            option.textContent = department;
            departmentFilter.appendChild(option);
        });
        
        situations.forEach(situation => {
            const option = document.createElement('option');
            option.value = situation;
            option.textContent = situation;
            situationFilter.appendChild(option);
        });
    }
    
    // Apply filters to data
    function applyFilters() {
        if (!originalData.employees.length) return;
        
        let absences = [...originalData.absences];
        let employees = [...originalData.employees];
        
        // Filter by date
        if (startDateFilter.value && endDateFilter.value) {
            const startDate = new Date(startDateFilter.value);
            const endDate = new Date(endDateFilter.value);
            
            absences = absences.filter(item => {
                if (!item.dt_inicio_atestado) return false;
                const absenceDate = new Date(item.dt_inicio_atestado);
                return absenceDate >= startDate && absenceDate <= endDate;
            });
        }
        
        // Filter by unit
        if (unitFilter.value) {
            absences = absences.filter(item => item.nome_unidade === unitFilter.value);
        }
        
        // Filter by department
        if (departmentFilter.value) {
            absences = absences.filter(item => item.nome_setor === departmentFilter.value);
        }
        
        // Filter by situation
        if (situationFilter.value) {
            employees = employees.filter(item => item.situacao === situationFilter.value);
            
            // Only include absences for employees with matching situation
            const filteredEmployeeMatriculas = employees.map(emp => emp.matricula_funcionario);
            absences = absences.filter(abs => 
                filteredEmployeeMatriculas.includes(abs.matricula_func)
            );
        }
        
        // Calculate metrics
        const totalAbsences = absences.length;
        const totalEmployees = employees.length;
        const totalDaysOff = _.sumBy(absences, item => parseInt(item.dias_afastados) || 0);
        const totalHoursOff = totalDaysOff * 8; // 8 hours per day
        
        // Calculate absenteeism rate
        const totalPotentialHours = totalEmployees * AVG_WORK_HOURS_PER_MONTH;
        const absenteeismRate = totalPotentialHours > 0 ? (totalHoursOff / totalPotentialHours) * 100 : 0;
        
        // Calculate absenteeism cost
        const absenteeismCost = totalHoursOff * HOURLY_RATE;
        
        // Calculate cost percentage of total wage
        const totalWage = totalEmployees * MIN_WAGE_BRAZIL;
        const costPercentage = totalWage > 0 ? (absenteeismCost / totalWage) * 100 : 0;
        
        // Group by unit
        const absencesByUnit = _.groupBy(absences, 'nome_unidade');
        const absencesByUnitStats = _.mapValues(absencesByUnit, group => {
            const daysOff = _.sumBy(group, item => parseInt(item.dias_afastados) || 0);
            return {
                total: group.length,
                daysOff: daysOff,
                hoursOff: daysOff * 8
            };
        });
        
        // Group by department
        const absencesByDepartment = _.groupBy(absences, 'nome_setor');
        const absencesByDepartmentStats = _.mapValues(absencesByDepartment, group => {
            const daysOff = _.sumBy(group, item => parseInt(item.dias_afastados) || 0);
            return {
                total: group.length,
                daysOff: daysOff,
                hoursOff: daysOff * 8
            };
        });
        
        // Group by CID
        const absencesByCID = _.groupBy(absences, 'grupo_patologico');
        const absencesByCIDStats = _.mapValues(absencesByCID, group => {
            const daysOff = _.sumBy(group, item => parseInt(item.dias_afastados) || 0);
            return {
                total: group.length,
                daysOff: daysOff,
                percentage: totalAbsences > 0 ? (group.length / totalAbsences) * 100 : 0
            };
        });
        
        // Group by month
        const absencesByMonth = _.groupBy(absences, item => {
            if (!item.dt_inicio_atestado) return 'Unknown';
            const date = new Date(item.dt_inicio_atestado);
            return `${date.getMonth() + 1}/${date.getFullYear()}`;
        });
        
        const absencesByMonthStats = _.mapValues(absencesByMonth, group => {
            const daysOff = _.sumBy(group, item => parseInt(item.dias_afastados) || 0);
            return {
                total: group.length,
                daysOff: daysOff,
                hoursOff: daysOff * 8
            };
        });
        
        // Group by gender
        const absencesByGender = _.groupBy(absences, 'sexo');
        const absencesByGenderStats = _.mapValues(absencesByGender, group => {
            const daysOff = _.sumBy(group, item => parseInt(item.dias_afastados) || 0);
            
            // Calculate main CIDs by gender
            const cidsByGender = _.groupBy(group, 'grupo_patologico');
            const mainCids = Object.entries(cidsByGender)
                .filter(([cid]) => cid && cid !== '')
                .map(([cid, items]) => ({
                    cid,
                    count: items.length,
                    percentage: (items.length / group.length) * 100
                }))
                .sort((a, b) => b.count - a.count);
            
            return {
                total: group.length,
                daysOff: daysOff,
                percentage: totalAbsences > 0 ? (group.length / totalAbsences) * 100 : 0,
                mainCids: mainCids.slice(0, 5) // Top 5 CIDs
            };
        });
        
        // Format data for charts
        const unitChartData = Object.entries(absencesByUnitStats)
            .map(([unit, stats]) => ({
                unit: unit.length > 20 ? unit.substring(0, 20) + '...' : unit,
                absences: stats.total,
                daysOff: stats.daysOff,
                hoursOff: stats.hoursOff
            }))
            .sort((a, b) => b.daysOff - a.daysOff)
            .slice(0, 10); // Top 10 units
        
        const departmentChartData = Object.entries(absencesByDepartmentStats)
            .map(([department, stats]) => ({
                department,
                absences: stats.total,
                daysOff: stats.daysOff,
                hoursOff: stats.hoursOff
            }))
            .sort((a, b) => b.daysOff - a.daysOff)
            .slice(0, 10); // Top 10 departments
        
        const cidChartData = Object.entries(absencesByCIDStats)
            .filter(([cid]) => cid && cid !== '') // Remove entries without CID
            .map(([cid, stats]) => ({
                cid: cid.length > 30 ? cid.substring(0, 30) + '...' : cid,
                absences: stats.total,
                daysOff: stats.daysOff,
                percentage: parseFloat(stats.percentage.toFixed(2))
            }))
            .sort((a, b) => b.absences - a.absences)
            .slice(0, 10); // Top 10 CIDs
        
        const genderChartData = Object.entries(absencesByGenderStats)
            .map(([gender, stats]) => ({
                gender: gender === "1" ? "Masculino" : gender === "2" ? "Feminino" : "Não informado",
                absences: stats.total,
                daysOff: stats.daysOff,
                percentage: parseFloat(stats.percentage.toFixed(2)),
                mainCids: stats.mainCids
            }));
        
        const monthChartData = Object.entries(absencesByMonthStats)
            .map(([month, stats]) => ({
                month,
                absences: stats.total,
                daysOff: stats.daysOff,
                hoursOff: stats.hoursOff
            }))
            .sort((a, b) => {
                // Sort by month and year
                const [monthA, yearA] = a.month.split('/');
                const [monthB, yearB] = b.month.split('/');
                
                if (yearA !== yearB) return parseInt(yearA) - parseInt(yearB);
                return parseInt(monthA) - parseInt(monthB);
            });
        
        // Store filtered data
        filteredData = {
            employees,
            absences,
            metrics: {
                totalAbsences,
                totalEmployees,
                totalDaysOff,
                totalHoursOff,
                absenteeismRate,
                absenteeismCost,
                costPercentage
            },
            charts: {
                byUnit: unitChartData,
                byDepartment: departmentChartData,
                byCID: cidChartData,
                byGender: genderChartData,
                byMonth: monthChartData
            }
        };
        
        // Update UI
        updateUI();
    }
    
    // Update UI with filtered data
    function updateUI() {
        if (!filteredData) return;
        
        // Update metrics
        absenteeismRateEl.textContent = formatPercent(filteredData.metrics.absenteeismRate);
        totalCostEl.textContent = formatCurrency(filteredData.metrics.absenteeismCost);
        totalDaysOffEl.textContent = filteredData.metrics.totalDaysOff;
        employeeVsAbsencesEl.textContent = `${filteredData.metrics.totalEmployees} / ${filteredData.metrics.totalAbsences}`;
        
        // Update filter summary
        updateFilterSummary();
        
        // Update hours data
        totalHoursOffEl.textContent = `${filteredData.metrics.totalHoursOff} horas`;
        
        // Update cost data
        totalCostValueEl.textContent = formatCurrency(filteredData.metrics.absenteeismCost);
        totalCostPercentEl.textContent = `Representa ${formatPercent(filteredData.metrics.costPercentage)} da folha salarial estimada`;
        
        // Update savings projections
        savings10El.textContent = formatCurrency(filteredData.metrics.absenteeismCost * 0.1);
        savings20El.textContent = formatCurrency(filteredData.metrics.absenteeismCost * 0.2);
        savings30El.textContent = formatCurrency(filteredData.metrics.absenteeismCost * 0.3);
        
        // Update unit chart
        updateChart(unitChart, 
            filteredData.charts.byUnit.map(item => item.unit),
            [
                filteredData.charts.byUnit.map(item => item.daysOff),
                filteredData.charts.byUnit.map(item => item.absences)
            ]
        );
        
        // Update department chart
        updateChart(departmentChart, 
            filteredData.charts.byDepartment.map(item => item.department),
            [
                filteredData.charts.byDepartment.map(item => item.daysOff),
                filteredData.charts.byDepartment.map(item => item.absences)
            ]
        );
        
        // Update CID chart
        updateChart(cidChart, 
            filteredData.charts.byCID.map(item => item.cid),
            [
                filteredData.charts.byCID.map(item => item.absences),
                filteredData.charts.byCID.map(item => item.daysOff)
            ]
        );
        
        // Update month chart
        updateChart(monthChart, 
            filteredData.charts.byMonth.map(item => item.month),
            [
                filteredData.charts.byMonth.map(item => item.daysOff),
                filteredData.charts.byMonth.map(item => item.absences)
            ]
        );
        
        // Update gender chart
        updateChart(genderChart,
            filteredData.charts.byGender.map(item => item.gender),
            [filteredData.charts.byGender.map(item => item.absences)]
        );
        
        // Update cost sector chart
        updateChart(costSectorChart,
            filteredData.charts.byDepartment.slice(0, 5).map(item => item.department),
            [filteredData.charts.byDepartment.slice(0, 5).map(item => item.hoursOff * HOURLY_RATE)]
        );
        
        // Update gender distribution
        updateGenderDistribution();
    }
    
    // Update filter summary
    function updateFilterSummary() {
        let filterText = 'Filtros aplicados: ';
        let filtersApplied = false;
        
        if (startDateFilter.value && endDateFilter.value) {
            filterText += `<span class="filter-badge">Período: ${formatDateBR(startDateFilter.value)} a ${formatDateBR(endDateFilter.value)}</span>`;
            filtersApplied = true;
        }
        
        if (unitFilter.value) {
            filterText += `<span class="filter-badge">Unidade: ${unitFilter.value}</span>`;
            filtersApplied = true;
        }
        
        if (departmentFilter.value) {
            filterText += `<span class="filter-badge">Setor: ${departmentFilter.value}</span>`;
            filtersApplied = true;
        }
        
        if (situationFilter.value) {
            filterText += `<span class="filter-badge">Situação: ${situationFilter.value}</span>`;
            filtersApplied = true;
        }
        
        if (!filtersApplied) {
            filterText += '<span class="text-muted">Nenhum filtro aplicado</span>';
        }
        
        activeFiltersEl.innerHTML = filterText;
        filteredRecordsEl.textContent = `Exibindo ${filteredData.absences.length} de ${originalData.absences.length} atestados`;
    }
    
    // Update chart with new data
    function updateChart(chart, labels, dataSets) {
        chart.data.labels = labels;
        
        dataSets.forEach((dataSet, index) => {
            chart.data.datasets[index].data = dataSet;
        });
        
        chart.update();
    }
    
    // Update gender distribution section
    function updateGenderDistribution() {
        // Update gender distribution cards
        const genderDistributionEl = document.getElementById('gender-distribution');
        const genderDaysOffEl = document.getElementById('gender-days-off');
        const genderCidTablesEl = document.getElementById('gender-cid-tables');
        
        // Clear previous data
        genderDistributionEl.innerHTML = '';
        genderDaysOffEl.innerHTML = '';
        genderCidTablesEl.innerHTML = '';
        
        // Add gender distribution cards
        filteredData.charts.byGender.forEach((gender, index) => {
            // Distribution cards
            const distributionCard = document.createElement('div');
            distributionCard.className = 'gender-card';
            distributionCard.innerHTML = `
                <p class="value" style="color: ${COLORS[index % COLORS.length]}">${gender.percentage.toFixed(2)}%</p>
                <p class="label">${gender.gender}</p>
            `;
            genderDistributionEl.appendChild(distributionCard);
            
            // Days off cards
            const daysOffCard = document.createElement('div');
            daysOffCard.className = 'gender-card';
            daysOffCard.innerHTML = `
                <p class="value" style="color: ${COLORS[index % COLORS.length]}">${gender.daysOff}</p>
                <p class="label">${gender.gender}</p>
            `;
            genderDaysOffEl.appendChild(daysOffCard);
            
            // CID tables
            const cidTable = document.createElement('div');
            cidTable.className = 'gender-cid-table';
            cidTable.style.borderColor = COLORS[index % COLORS.length];
            
            let tableHTML = `
                <h4 style="color: ${COLORS[index % COLORS.length]}">${gender.gender}</h4>
                <table class="cid-table">
                    <thead>
                        <tr>
                            <th>Grupo Patológico (CID)</th>
                            <th>Qtde</th>
                            <th>%</th>
                        </tr>
                    </thead>
                    <tbody>
            `;
            
            if (gender.mainCids && gender.mainCids.length > 0) {
                gender.mainCids.forEach(cid => {
                    tableHTML += `
                        <tr>
                            <td>${cid.cid.length > 25 ? cid.cid.substring(0, 25) + '...' : cid.cid}</td>
                            <td>${cid.count}</td>
                            <td>${cid.percentage.toFixed(1)}%</td>
                        </tr>
                    `;
                });
            } else {
                tableHTML += `
                    <tr>
                        <td colspan="3" class="text-muted" style="text-align: center;">Nenhum dado disponível</td>
                    </tr>
                `;
            }
            
            tableHTML += `
                    </tbody>
                </table>
            `;
            
            cidTable.innerHTML = tableHTML;
            genderCidTablesEl.appendChild(cidTable);
        });
    }
    
    // Reset all filters
    function resetFilters() {
        // Find min and max dates
        const dates = originalData.absences
            .filter(item => item.dt_inicio_atestado)
            .map(item => new Date(item.dt_inicio_atestado));
        
        if (dates.length > 0) {
            const minDate = new Date(Math.min(...dates));
            const maxDate = new Date(Math.max(...dates));
            
            startDateFilter.value = formatDateForInput(minDate);
            endDateFilter.value = formatDateForInput(maxDate);
        }
        
        unitFilter.value = '';
        departmentFilter.value = '';
        situationFilter.value = '';
        
        applyFilters();
    }
    
    // Helper Functions
    
    // Format currency
    function formatCurrency(value) {
        return `R$ ${value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
    }
    
    // Format percentage
    function formatPercent(value) {
        return `${value.toLocaleString('pt-BR', { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
    }
    
    // Format date for input (YYYY-MM-DD)
    function formatDateForInput(date) {
        return `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
    }
    
    // Format date for display (DD/MM/YYYY)
    function formatDateBR(dateStr) {
        if (!dateStr) return "";
        const [year, month, day] = dateStr.split('-');
        return `${day}/${month}/${year}`;
    }
    
    // Show loading overlay
    function showLoading() {
        loadingOverlay.style.display = 'flex';
    }
    
    // Hide loading overlay
    function hideLoading() {
        loadingOverlay.style.display = 'none';
    }
});
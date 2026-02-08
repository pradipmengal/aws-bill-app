document.addEventListener('DOMContentLoaded', () => {
    // State
    let dailyChart = null;
    let serviceChart = null;
    let regionChart = null;

    // Elements
    const startDateInput = document.getElementById('startDate');
    const endDateInput = document.getElementById('endDate');
    const updateBtn = document.getElementById('updateBtn');
    const logoutBtn = document.getElementById('logoutBtn');
    const themeToggle = document.getElementById('themeToggle');
    const loader = document.getElementById('loader');

    const loginModal = document.getElementById('loginModal');
    const loginForm = document.getElementById('loginForm');
    const demoBtn = document.getElementById('demoBtn');
    const loginError = document.getElementById('loginError');

    const totalCostDisplay = document.getElementById('totalCostDisplay');
    const dateRangeDisplay = document.getElementById('dateRangeDisplay');
    const topServiceDisplay = document.getElementById('topServiceDisplay');
    const topServiceAmount = document.getElementById('topServiceAmount');
    const topRegionDisplay = document.getElementById('topRegionDisplay');
    const topRegionAmount = document.getElementById('topRegionAmount');

    // Initialization
    initializeDates();
    initializeTheme();
    checkAuth();

    // Event Listeners
    updateBtn.addEventListener('click', fetchAllData);
    logoutBtn.addEventListener('click', logout);
    themeToggle.addEventListener('click', toggleTheme);

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const accessKey = document.getElementById('accessKey').value.trim();
        const secretKey = document.getElementById('secretKey').value.trim();

        if (accessKey && secretKey) {
            sessionStorage.setItem('aws_access_key', accessKey);
            sessionStorage.setItem('aws_secret_key', secretKey);
            sessionStorage.setItem('auth_mode', 'credentials');

            const success = await fetchAllData();
            if (success) {
                hideLoginModal();
            }
        }
    });

    demoBtn.addEventListener('click', async () => {
        sessionStorage.setItem('auth_mode', 'demo');
        const success = await fetchAllData();
        if (success) {
            hideLoginModal();
        }
    });

    function initializeTheme() {
        const savedTheme = localStorage.getItem('theme') || 'dark';
        document.documentElement.setAttribute('data-theme', savedTheme);
        updateThemeIcon(savedTheme);
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';

        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        updateThemeIcon(newTheme);

        // Re-render charts to update colors
        fetchAllData();
    }

    function updateThemeIcon(theme) {
        const icon = themeToggle.querySelector('i');
        if (theme === 'light') {
            icon.classList.remove('fa-sun');
            icon.classList.add('fa-moon');
        } else {
            icon.classList.remove('fa-moon');
            icon.classList.add('fa-sun');
        }
    }

    async function checkAuth() {
        const authMode = sessionStorage.getItem('auth_mode');

        if (authMode) {
            // User had a session, verify it still works before hiding modal
            const success = await fetchAllData();
            if (success) {
                hideLoginModal();
                return;
            }
        }

        // No session or verification failed
        showLoginModal();
    }

    function initializeDates() {
        if (!startDateInput || !endDateInput) return;
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        startDateInput.valueAsDate = firstDay;
        endDateInput.valueAsDate = today;
        if (dateRangeDisplay) {
            updateDateRangeDisplay();
        }
    }

    function updateDateRangeDisplay() {
        if (!startDateInput.value || !endDateInput.value || !dateRangeDisplay) return;
        const start = new Date(startDateInput.value);
        const end = new Date(endDateInput.value);
        const options = { month: 'short', day: 'numeric', year: 'numeric' };
        dateRangeDisplay.textContent = `${start.toLocaleDateString('en-US', options)} - ${end.toLocaleDateString('en-US', options)}`;
    }

    function showLoginModal() {
        loginModal.classList.remove('hidden');
        logoutBtn.classList.add('hidden');
    }

    function hideLoginModal() {
        loginModal.classList.add('hidden');
        logoutBtn.classList.remove('hidden');
        clearError();
    }

    function displayError(msg) {
        if (!loginError) return;
        loginError.textContent = msg;
        loginError.classList.remove('hidden');
    }

    function clearError() {
        if (!loginError) return;
        loginError.textContent = '';
        loginError.classList.add('hidden');
    }

    function logout() {
        sessionStorage.removeItem('aws_access_key');
        sessionStorage.removeItem('aws_secret_key');
        sessionStorage.removeItem('auth_mode');

        // Reset UI
        document.getElementById('accessKey').value = '';
        document.getElementById('secretKey').value = '';
        clearError();

        showLoginModal();
    }

    function getHeaders() {
        const authMode = sessionStorage.getItem('auth_mode');
        const headers = {
            'Content-Type': 'application/json'
        };

        // Add credentials if available
        if (authMode === 'credentials') {
            const ak = sessionStorage.getItem('aws_access_key');
            const sk = sessionStorage.getItem('aws_secret_key');
            if (ak && sk) {
                headers['x-aws-access-key-id'] = ak;
                headers['x-aws-secret-access-key'] = sk;
            }
        } else if (authMode === 'demo') {
            headers['x-use-demo-data'] = 'true';
        }

        return headers;
    }

    async function fetchAllData() {
        showLoader();
        clearError();

        // Update date range display
        updateDateRangeDisplay();

        const startDate = startDateInput.value;
        const endDate = endDateInput.value;

        try {
            const headers = getHeaders();

            // Fetch all four endpoints in parallel with date parameters
            const [dailyResponse, serviceResponse, regionResponse, breakdownResponse] = await Promise.all([
                fetch(`/daily-cost?start_date=${startDate}&end_date=${endDate}`, { headers }),
                fetch(`/service-cost?start_date=${startDate}&end_date=${endDate}`, { headers }),
                fetch(`/region-cost?start_date=${startDate}&end_date=${endDate}`, { headers }),
                fetch(`/region-service-breakdown?start_date=${startDate}&end_date=${endDate}`, { headers })
            ]);

            // Check for errors
            if (!dailyResponse.ok) {
                const errorData = await dailyResponse.json();
                handleError(dailyResponse.status, errorData.detail);
                return false;
            }
            if (!serviceResponse.ok) {
                const errorData = await serviceResponse.json();
                handleError(serviceResponse.status, errorData.detail);
                return false;
            }
            if (!regionResponse.ok) {
                const errorData = await regionResponse.json();
                handleError(regionResponse.status, errorData.detail);
                return false;
            }
            if (!breakdownResponse.ok) {
                const errorData = await breakdownResponse.json();
                handleError(breakdownResponse.status, errorData.detail);
                return false;
            }

            // Parse responses
            const dailyData = await dailyResponse.json();
            const serviceData = await serviceResponse.json();
            const regionData = await regionResponse.json();
            const breakdownData = await breakdownResponse.json();

            // Update dashboard
            updateDashboard(dailyData, serviceData, regionData, breakdownData);
            return true;

        } catch (error) {
            console.error('Error:', error);
            if (loginModal.classList.contains('hidden')) {
                alert(`Error: ${error.message}`);
            } else {
                displayError(`Error: ${error.message}`);
            }
            return false;
        } finally {
            hideLoader();
        }
    }

    function handleError(status, detail) {
        if (status === 401) {
            displayError("Invalid AWS credentials. Please double-check your Access Key and Secret Key.");
            logout();
        } else if (status === 403) {
            displayError("Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions.");
        } else {
            displayError(detail || 'An error occurred');
        }
    }

    function updateDashboard(dailyData, serviceData, regionData, breakdownData) {
        // Update summary cards
        const totalCost = serviceData.total_cost || regionData.total_cost || 0;
        totalCostDisplay.textContent = formatCurrency(totalCost);

        // Calculate yesterday's cost (last entry in daily costs)
        const dailyCosts = dailyData.daily_costs || [];
        const yesterdayCost = dailyCosts.length > 0 ? dailyCosts[dailyCosts.length - 1].cost : 0;
        const yesterdayCostDisplay = document.getElementById('yesterdayCostDisplay');
        if (yesterdayCostDisplay) {
            yesterdayCostDisplay.textContent = formatCurrency(yesterdayCost);
        }

        // Find top service
        const services = serviceData.services || {};
        let topService = '-';
        let topServiceCost = 0;
        for (const [service, cost] of Object.entries(services)) {
            if (cost > topServiceCost) {
                topServiceCost = cost;
                topService = service;
            }
        }
        topServiceDisplay.textContent = topService;
        topServiceAmount.textContent = formatCurrency(topServiceCost);

        // Find top region
        const regions = regionData.regions || {};
        let topRegion = '-';
        let topRegionCost = 0;
        for (const [region, cost] of Object.entries(regions)) {
            if (cost > topRegionCost) {
                topRegionCost = cost;
                topRegion = region;
            }
        }
        topRegionDisplay.textContent = topRegion;
        topRegionAmount.textContent = formatCurrency(topRegionCost);

        // Render charts
        renderDailyChart(dailyData);
        renderServiceChart(serviceData);
        renderRegionChart(regionData);

        // Render breakdown table
        renderBreakdownTable(breakdownData);
    }

    function renderDailyChart(data) {
        const ctx = document.getElementById('dailyChart').getContext('2d');
        const dailyCosts = data.daily_costs || [];

        const labels = dailyCosts.map(d => d.date);
        const values = dailyCosts.map(d => d.cost);

        if (dailyChart) {
            dailyChart.destroy();
        }

        dailyChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Daily Cost ($)',
                    data: values,
                    borderColor: '#8b5cf6',
                    backgroundColor: 'rgba(139, 92, 246, 0.1)',
                    borderWidth: 2,
                    fill: true,
                    tension: 0.4,
                    pointBackgroundColor: '#8b5cf6',
                    pointBorderColor: '#fff',
                    pointBorderWidth: 2,
                    pointRadius: 4,
                    pointHoverRadius: 6
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: isLightMode() ? 'rgba(255, 255, 255, 0.95)' : 'rgba(30, 41, 59, 0.9)',
                        titleColor: isLightMode() ? '#0f172a' : '#f8fafc',
                        bodyColor: isLightMode() ? '#334155' : '#e2e8f0',
                        borderColor: isLightMode() ? 'rgba(0,0,0,0.1)' : 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                        displayColors: false,
                        callbacks: {
                            label: function (context) {
                                return formatCurrency(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim()
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
                            font: {
                                family: "'Outfit', sans-serif"
                            },
                            callback: function (value) {
                                return '$' + value;
                            }
                        },
                        border: {
                            display: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
                            font: {
                                family: "'Outfit', sans-serif"
                            }
                        },
                        border: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    function renderServiceChart(data) {
        const ctx = document.getElementById('serviceChart').getContext('2d');
        const services = data.services || {};

        const labels = Object.keys(services);
        const values = Object.values(services);

        if (serviceChart) {
            serviceChart.destroy();
        }

        const colors = generateColors(labels.length);

        serviceChart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: isLightMode() ? '#fff' : '#1e293b'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
                            font: {
                                family: "'Outfit', sans-serif",
                                size: 11
                            },
                            padding: 10,
                            usePointStyle: true
                        }
                    },
                    tooltip: {
                        backgroundColor: isLightMode() ? 'rgba(255, 255, 255, 0.95)' : 'rgba(30, 41, 59, 0.9)',
                        titleColor: isLightMode() ? '#0f172a' : '#f8fafc',
                        bodyColor: isLightMode() ? '#334155' : '#e2e8f0',
                        borderColor: isLightMode() ? 'rgba(0,0,0,0.1)' : 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                        callbacks: {
                            label: function (context) {
                                const label = context.label || '';
                                const value = formatCurrency(context.raw);
                                return `${label}: ${value}`;
                            }
                        }
                    }
                }
            }
        });
    }

    function renderRegionChart(data) {
        const ctx = document.getElementById('regionChart').getContext('2d');
        const regions = data.regions || {};

        const labels = Object.keys(regions);
        const values = Object.values(regions);

        if (regionChart) {
            regionChart.destroy();
        }

        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, '#8b5cf6');
        gradient.addColorStop(1, '#0ea5e9');

        regionChart = new Chart(ctx, {
            type: 'bar',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Cost ($)',
                    data: values,
                    backgroundColor: gradient,
                    borderRadius: 8,
                    hoverBackgroundColor: '#a78bfa',
                    barThickness: 'flex',
                    maxBarThickness: 50
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        backgroundColor: isLightMode() ? 'rgba(255, 255, 255, 0.95)' : 'rgba(30, 41, 59, 0.9)',
                        titleColor: isLightMode() ? '#0f172a' : '#f8fafc',
                        bodyColor: isLightMode() ? '#334155' : '#e2e8f0',
                        borderColor: isLightMode() ? 'rgba(0,0,0,0.1)' : 'rgba(255, 255, 255, 0.1)',
                        borderWidth: 1,
                        padding: 12,
                        cornerRadius: 12,
                        displayColors: false,
                        callbacks: {
                            label: function (context) {
                                return formatCurrency(context.raw);
                            }
                        }
                    }
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-grid').trim()
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
                            font: {
                                family: "'Outfit', sans-serif"
                            },
                            callback: function (value) {
                                return '$' + value;
                            }
                        },
                        border: {
                            display: false
                        }
                    },
                    x: {
                        grid: {
                            display: false
                        },
                        ticks: {
                            color: getComputedStyle(document.documentElement).getPropertyValue('--chart-text').trim(),
                            font: {
                                family: "'Outfit', sans-serif"
                            }
                        },
                        border: {
                            display: false
                        }
                    }
                }
            }
        });
    }

    function renderBreakdownTable(data) {
        const tableBody = document.querySelector('#breakdownTable tbody');
        if (!tableBody) return;

        tableBody.innerHTML = '';
        const totalCost = data.total_cost || 0;
        const regions = data.regions || {};

        // Convert to array and sort by total cost descending
        const regionEntries = Object.entries(regions).sort((a, b) => b[1].total - a[1].total);

        regionEntries.forEach(([regionName, regionData], index) => {
            const percentage = totalCost > 0 ? ((regionData.total / totalCost) * 100).toFixed(1) : '0.0';
            const rowId = `breakdown-row-${index}`;

            // Main region row
            const tr = document.createElement('tr');
            tr.className = 'main-row';
            tr.onclick = () => toggleRow(rowId, tr);
            tr.innerHTML = `
                <td>
                    <div style="display: flex; align-items: center; gap: 0.5rem;">
                        <i class="fa-solid fa-chevron-right row-toggle-icon"></i>
                        <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-gradient);"></span>
                        ${regionName}
                    </div>
                </td>
                <td style="font-weight: 500;">${formatCurrency(regionData.total)}</td>
                <td>
                    <div style="display: flex; align-items: center; gap: 0.75rem;">
                        <span style="min-width: 45px; font-size: 0.9rem; color: var(--text-secondary);">${percentage}%</span>
                        <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                            <div style="width: ${percentage}%; height: 100%; background: var(--accent-gradient); border-radius: 3px;"></div>
                        </div>
                    </div>
                </td>
            `;
            tableBody.appendChild(tr);

            // Nested services row
            const detailsTr = document.createElement('tr');
            detailsTr.className = 'nested-row';
            detailsTr.id = rowId;

            let detailsHtml = `
                <td colspan="3">
                    <table class="nested-table">
            `;

            const services = Object.entries(regionData.services).sort((a, b) => b[1] - a[1]);
            services.forEach(([serviceName, cost]) => {
                detailsHtml += `
                    <tr>
                        <td style="padding-left: 2rem;">${serviceName}</td>
                        <td>${formatCurrency(cost)}</td>
                        <td></td>
                    </tr>
                `;
            });

            detailsHtml += `
                    </table>
                </td>
            `;
            detailsTr.innerHTML = detailsHtml;
            tableBody.appendChild(detailsTr);
        });
    }

    function toggleRow(rowId, mainRow) {
        const detailsRow = document.getElementById(rowId);
        if (detailsRow) {
            detailsRow.classList.toggle('show');
            mainRow.classList.toggle('expanded');
        }
    }

    function generateColors(count) {
        const baseColors = [
            '#8b5cf6', '#0ea5e9', '#10b981', '#f59e0b',
            '#ef4444', '#ec4899', '#14b8a6', '#f97316'
        ];

        const colors = [];
        for (let i = 0; i < count; i++) {
            colors.push(baseColors[i % baseColors.length]);
        }
        return colors;
    }

    function isLightMode() {
        return document.documentElement.getAttribute('data-theme') === 'light';
    }

    function formatCurrency(amount) {
        if (isNaN(parseFloat(amount))) {
            return amount;
        }
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD'
        }).format(amount);
    }

    function showLoader() {
        loader.classList.remove('hidden');
    }

    function hideLoader() {
        loader.classList.add('hidden');
    }
});

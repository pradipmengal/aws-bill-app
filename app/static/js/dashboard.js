document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentData = null;
    let currentView = 'regions'; // 'regions' or 'consolidated'

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
    const topRegionDisplay = document.getElementById('topRegionDisplay');
    const topRegionAmount = document.getElementById('topRegionAmount');
    const tableBody = document.querySelector('#costTable tbody');
    const viewBtns = document.querySelectorAll('.view-btn');
    const chartTitle = document.querySelector('.chart-card h3');

    let regionChart = null;

    // Initialization
    initializeDates();
    initializeTheme();
    checkAuth();

    // Event Listeners
    updateBtn.addEventListener('click', fetchData);
    logoutBtn.addEventListener('click', logout);
    themeToggle.addEventListener('click', toggleTheme);

    viewBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            const view = e.target.dataset.view;
            switchView(view);
        });
    });

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const accessKey = document.getElementById('accessKey').value.trim();
        const secretKey = document.getElementById('secretKey').value.trim();

        if (accessKey && secretKey) {
            sessionStorage.setItem('aws_access_key', accessKey);
            sessionStorage.setItem('aws_secret_key', secretKey);
            sessionStorage.setItem('auth_mode', 'credentials');

            const success = await fetchData();
            if (success) {
                hideLoginModal();
            }
        }
    });

    demoBtn.addEventListener('click', async () => {
        sessionStorage.setItem('auth_mode', 'demo');
        const success = await fetchData();
        if (success) {
            hideLoginModal();
        }
    });

    function initializeDates() {
        const today = new Date();
        const firstDay = new Date(today.getFullYear(), today.getMonth(), 1);
        const lastDay = new Date(today.getFullYear(), today.getMonth() + 1, 0);

        startDateInput.valueAsDate = firstDay;
        endDateInput.valueAsDate = lastDay;
    }

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

        // Re-render chart to update colors
        if (currentData) {
            renderChart(currentData);
        }
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
            const success = await fetchData();
            if (success) {
                hideLoginModal();
                return;
            }
        }

        // No session or verification failed
        showLoginModal();
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

    function switchView(view) {
        currentView = view;

        // Update buttons
        viewBtns.forEach(btn => {
            if (btn.dataset.view === view) btn.classList.add('active');
            else btn.classList.remove('active');
        });

        if (currentData) {
            updateDashboard(currentData);
        }
    }

    async function fetchData() {
        showLoader();

        const start = startDateInput.value;
        const end = endDateInput.value;
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

        try {
            clearError();
            const response = await fetch(`/api/billing?start_date=${start}&end_date=${end}`, {
                headers: headers
            });

            if (!response.ok) {
                const errorData = await response.json();

                if (response.status === 401) {
                    displayError("Invalid AWS credentials. Please double-check your Access Key and Secret Key.");
                    logout();
                    return false;
                } else if (response.status === 403) {
                    displayError("Access denied. Your AWS user needs 'ce:GetCostAndUsage' permissions to view billing data.");
                    return false;
                }

                throw new Error(errorData.detail || 'Failed to fetch data');
            }

            const data = await response.json();
            currentData = data; // Store globally
            updateDashboard(data);
            return true;
        } catch (error) {
            console.error('Error:', error);
            // Show non-auth errors in dashboard context if modal is hidden
            if (loginModal.classList.contains('hidden')) {
                if (error.message && !error.message.includes('object Object')) {
                    alert(`Error: ${error.message}`);
                }
            } else {
                displayError(`Error: ${error.message}`);
            }
            return false;
        } finally {
            hideLoader();
        }
    }

    function updateDashboard(data) {
        // 1. Update Summary Cards
        totalCostDisplay.textContent = formatCurrency(data.total_cost);

        // Find top region or service based on view
        let topItemName = '-';
        let topItemAmount = 0;
        let sourceObj = {};

        if (currentView === 'regions') {
            sourceObj = data.regions;
            // Calculate top region manually because structure changed
            let maxVal = -1;
            for (const [key, val] of Object.entries(sourceObj)) {
                if (val.total > maxVal) {
                    maxVal = val.total;
                    topItemName = key;
                }
            }
            topItemAmount = maxVal > -1 ? maxVal : 0;
            document.querySelector('.trend-card h3').textContent = 'Top Region';
            chartTitle.textContent = 'Region-wise Distribution';

        } else {
            sourceObj = data.consolidated;
            let maxVal = -1;
            for (const [key, val] of Object.entries(sourceObj)) {
                if (val.total > maxVal) {
                    maxVal = val.total;
                    topItemName = key;
                }
            }
            topItemAmount = maxVal > -1 ? maxVal : 0;
            document.querySelector('.trend-card h3').textContent = 'Top Service';
            chartTitle.textContent = 'Service-wise Distribution';
        }

        topRegionDisplay.textContent = topItemName;
        topRegionAmount.textContent = formatCurrency(topItemAmount);

        // 2. Update Chart
        renderChart(data);

        // 3. Update Table
        updateTable(data);
    }

    function renderChart(data) {
        const ctx = document.getElementById('regionChart').getContext('2d');
        let labels = [];
        let values = [];

        if (currentView === 'regions') {
            labels = Object.keys(data.regions);
            values = labels.map(r => data.regions[r].total);
        } else {
            labels = Object.keys(data.consolidated);
            values = labels.map(s => data.consolidated[s].total);
        }

        if (regionChart) {
            regionChart.destroy();
        }

        // Create a gradient for the bars
        const gradient = ctx.createLinearGradient(0, 0, 0, 400);
        gradient.addColorStop(0, '#8b5cf6');   // Violet
        gradient.addColorStop(1, '#0ea5e9');   // Sky Blue

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

    function isLightMode() {
        return document.documentElement.getAttribute('data-theme') === 'light';
    }

    function updateTable(data) {
        tableBody.innerHTML = '';
        const totalCost = data.total_cost;

        let items = [];

        if (currentView === 'regions') {
            items = Object.entries(data.regions).map(([k, v]) => ({
                name: k,
                amount: v.total,
                details: v.services
            }));
        } else {
            items = Object.entries(data.consolidated).map(([k, v]) => ({
                name: k,
                amount: v.total,
                details: null // Could add region breakdown here if we wanted deeper nesting
            }));
        }

        // Sort descending
        items.sort((a, b) => b.amount - a.amount);

        items.forEach((item, index) => {
            const tr = document.createElement('tr');
            tr.className = 'main-row';
            const percentage = totalCost > 0 ? ((item.amount / totalCost) * 100).toFixed(1) : '0.0';
            const rowId = `row-${index}`;

            // Toggle logic for regions view
            if (currentView === 'regions') {
                tr.onclick = () => toggleRow(rowId, tr);
                tr.innerHTML = `
                    <td>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <i class="fa-solid fa-chevron-right row-toggle-icon"></i>
                            <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-gradient);"></span>
                            ${item.name}
                        </div>
                    </td>
                    <td style="font-weight: 500;">${formatCurrency(item.amount)}</td>
                    <td>
                         <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="min-width: 45px; font-size: 0.9rem; color: var(--text-secondary);">${percentage}%</span>
                            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                                <div style="width: ${percentage}%; height: 100%; background: var(--accent-gradient); border-radius: 3px;"></div>
                            </div>
                        </div>
                    </td>
                `;
            } else {
                tr.innerHTML = `
                    <td>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                             <span style="width: 8px; height: 8px; border-radius: 50%; background: var(--accent-gradient);"></span>
                            ${item.name}
                        </div>
                    </td>
                    <td style="font-weight: 500;">${formatCurrency(item.amount)}</td>
                    <td>
                         <div style="display: flex; align-items: center; gap: 0.75rem;">
                            <span style="min-width: 45px; font-size: 0.9rem; color: var(--text-secondary);">${percentage}%</span>
                            <div style="width: 100%; height: 6px; background: rgba(255,255,255,0.05); border-radius: 3px; overflow: hidden;">
                                <div style="width: ${percentage}%; height: 100%; background: var(--accent-gradient); border-radius: 3px;"></div>
                            </div>
                        </div>
                    </td>
                `;
            }

            tableBody.appendChild(tr);

            // Add details row if it's region view
            if (currentView === 'regions') {
                const detailsTr = document.createElement('tr');
                detailsTr.className = 'nested-row';
                detailsTr.id = rowId;

                let detailsHtml = `
                    <td colspan="3">
                        <table class="nested-table">
                `;

                const services = Object.entries(item.details).sort((a, b) => b[1] - a[1]);
                services.forEach(([svc, amount]) => {
                    detailsHtml += `
                        <tr>
                            <td>${svc}</td>
                            <td>${formatCurrency(amount)}</td>
                        </tr>
                     `;
                });

                detailsHtml += `
                        </table>
                    </td>
                `;
                detailsTr.innerHTML = detailsHtml;
                tableBody.appendChild(detailsTr);
            }
        });
    }

    function toggleRow(rowId, mainRow) {
        const detailsRow = document.getElementById(rowId);
        detailsRow.classList.toggle('show');
        mainRow.classList.toggle('expanded');
    }

    function formatCurrency(amount) {
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

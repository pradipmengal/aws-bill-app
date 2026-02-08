document.addEventListener('DOMContentLoaded', () => {
    // State
    let currentUsageData = null;
    let currentView = 'regions';
    let sortState = { column: 'service', direction: 'asc' }; // service, count, cost

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

    const totalResourcesDisplay = document.getElementById('totalResourcesDisplay');
    const usageTableBody = document.querySelector('#usageTable tbody');
    const usageSearch = document.getElementById('usageSearch');
    const viewBtns = document.querySelectorAll('.view-btn');
    const usageTableHeaders = document.querySelectorAll('#usageTable th');

    // Initialization
    initializeDates();
    initializeTheme();
    checkAuth();

    // Event Listeners
    updateBtn.addEventListener('click', fetchUsageData);
    logoutBtn.addEventListener('click', logout);
    themeToggle.addEventListener('click', toggleTheme);

    viewBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            currentView = e.target.dataset.view;
            viewBtns.forEach(b => b.classList.remove('active'));
            e.target.classList.add('active');
            if (currentUsageData) renderUsageTable(currentUsageData);
        });
    });

    usageTableHeaders.forEach(header => {
        if (header.textContent.includes('Service') || header.textContent.includes('Count') || header.textContent.includes('Cost')) {
            header.style.cursor = 'pointer';
            header.addEventListener('click', () => {
                const column = header.textContent.includes('Service') ? 'service' :
                    header.textContent.includes('Count') ? 'count' : 'cost';

                if (sortState.column === column) {
                    sortState.direction = sortState.direction === 'asc' ? 'desc' : 'asc';
                } else {
                    sortState.column = column;
                    sortState.direction = 'desc'; // Default to desc for count/cost
                    if (column === 'service') sortState.direction = 'asc';
                }

                updateSortIcons();
                if (currentUsageData) renderUsageTable(currentUsageData);
            });
        }
    });

    function updateSortIcons() {
        usageTableHeaders.forEach(header => {
            header.querySelectorAll('.sort-icon').forEach(i => i.remove());
            const col = header.textContent.includes('Service') ? 'service' :
                header.textContent.includes('Count') ? 'count' : 'cost';

            if (sortState.column === col) {
                const icon = document.createElement('i');
                icon.className = `fa-solid fa-sort-${sortState.direction === 'asc' ? 'up' : 'down'} sort-icon`;
                icon.style.marginLeft = '0.5rem';
                icon.style.color = 'var(--accent-primary)';
                header.appendChild(icon);
            }
        });
    }

    if (usageSearch) {
        usageSearch.addEventListener('input', () => {
            if (currentUsageData) renderUsageTable(currentUsageData);
        });
    }

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        const accessKey = document.getElementById('accessKey').value.trim();
        const secretKey = document.getElementById('secretKey').value.trim();

        if (accessKey && secretKey) {
            sessionStorage.setItem('aws_access_key', accessKey);
            sessionStorage.setItem('aws_secret_key', secretKey);
            sessionStorage.setItem('auth_mode', 'credentials');

            const success = await fetchUsageData();
            if (success) hideLoginModal();
        }
    });

    demoBtn.addEventListener('click', async () => {
        sessionStorage.setItem('auth_mode', 'demo');
        const success = await fetchUsageData();
        if (success) hideLoginModal();
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
    }

    function toggleTheme() {
        const currentTheme = document.documentElement.getAttribute('data-theme');
        const newTheme = currentTheme === 'light' ? 'dark' : 'light';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
    }

    async function checkAuth() {
        const authMode = sessionStorage.getItem('auth_mode');
        if (authMode) {
            const success = await fetchUsageData();
            if (success) {
                hideLoginModal();
                return;
            }
        }
        showLoginModal();
    }

    function showLoginModal() {
        loginModal.classList.remove('hidden');
        logoutBtn.classList.add('hidden');
    }

    function hideLoginModal() {
        loginModal.classList.add('hidden');
        logoutBtn.classList.remove('hidden');
    }

    function logout() {
        sessionStorage.clear();
        window.location.href = '/';
    }

    async function fetchUsageData() {
        showLoader();
        const start = startDateInput.value;
        const end = endDateInput.value;
        const authMode = sessionStorage.getItem('auth_mode');

        const headers = { 'Content-Type': 'application/json' };
        if (authMode === 'credentials') {
            headers['x-aws-access-key-id'] = sessionStorage.getItem('aws_access_key');
            headers['x-aws-secret-access-key'] = sessionStorage.getItem('aws_secret_key');
        } else if (authMode === 'demo') {
            headers['x-use-demo-data'] = 'true';
        }

        try {
            const response = await fetch(`/api/usage?start_date=${start}&end_date=${end}`, { headers });
            if (!response.ok) throw new Error('Failed to fetch usage data');

            const data = await response.json();
            currentUsageData = data;
            updateSortIcons();
            renderUsageDashboard(data);
            return true;
        } catch (error) {
            console.error('Error:', error);
            alert('Failed to load usage data');
            return false;
        } finally {
            hideLoader();
        }
    }

    function renderUsageDashboard(data) {
        // Calculate total distinct components
        let components = new Set();
        Object.values(data.consolidated).forEach(list => {
            list.forEach(item => components.add(item.component));
        });
        totalResourcesDisplay.textContent = components.size;

        renderUsageTable(data);
    }

    function renderUsageTable(data) {
        usageTableBody.innerHTML = '';
        const searchTerm = usageSearch ? usageSearch.value.toLowerCase() : '';

        if (currentView === 'regions') {
            Object.entries(data.regions).forEach(([region, services]) => {
                let regionHasMatch = false;
                const filteredServices = {};

                Object.entries(services).forEach(([service, components]) => {
                    const matchedComponents = components.filter(comp =>
                        service.toLowerCase().includes(searchTerm) ||
                        comp.component.toLowerCase().includes(searchTerm)
                    );
                    if (matchedComponents.length > 0) {
                        filteredServices[service] = matchedComponents;
                        regionHasMatch = true;
                    }
                });

                if (regionHasMatch || region.toLowerCase().includes(searchTerm)) {
                    // Region Header Row
                    const regionHeader = document.createElement('tr');
                    regionHeader.className = 'region-group-header';
                    regionHeader.innerHTML = `<td colspan="4" style="background: rgba(139, 92, 246, 0.1); font-weight: 700; color: var(--accent-primary);"><i class="fa-solid fa-location-dot"></i> ${region}</td>`;
                    usageTableBody.appendChild(regionHeader);

                    // Flatten and sort components for this region
                    let flatComponents = [];
                    Object.entries(filteredServices).forEach(([service, components]) => {
                        components.forEach(comp => flatComponents.push({ ...comp, service }));
                    });

                    flatComponents.sort((a, b) => {
                        let valA, valB;
                        if (sortState.column === 'service') {
                            valA = a.service + a.component;
                            valB = b.service + b.component;
                        } else {
                            valA = a[sortState.column];
                            valB = b[sortState.column];
                        }

                        if (sortState.direction === 'asc') return valA > valB ? 1 : -1;
                        return valA < valB ? 1 : -1;
                    });

                    flatComponents.forEach(comp => {
                        const tr = document.createElement('tr');
                        tr.innerHTML = `
                            <td>
                                <div style="display: flex; flex-direction: column;">
                                    <span style="font-size: 0.75rem; color: var(--text-secondary);">${comp.service}</span>
                                    <span style="font-weight: 500;">${comp.component}</span>
                                </div>
                            </td>
                            <td style="font-weight: 600; color: var(--accent-secondary);">${comp.count}</td>
                            <td style="color: var(--text-secondary); font-size: 0.85rem;">${comp.unit}</td>
                            <td style="font-weight: 600; color: var(--text-primary);">${formatCurrency(comp.cost)}</td>
                        `;
                        usageTableBody.appendChild(tr);
                    });
                }
            });
        } else {
            let flatList = [];
            Object.entries(data.consolidated).forEach(([service, components]) => {
                components.forEach(comp => {
                    if (service.toLowerCase().includes(searchTerm) || comp.component.toLowerCase().includes(searchTerm)) {
                        flatList.push({ ...comp, service });
                    }
                });
            });

            flatList.sort((a, b) => {
                let valA, valB;
                if (sortState.column === 'service') {
                    valA = a.service + a.component;
                    valB = b.service + b.component;
                } else {
                    valA = a[sortState.column];
                    valB = b[sortState.column];
                }

                if (sortState.direction === 'asc') return valA > valB ? 1 : -1;
                return valA < valB ? 1 : -1;
            });

            flatList.forEach(comp => {
                const tr = document.createElement('tr');
                tr.innerHTML = `
                    <td>
                         <div style="display: flex; flex-direction: column;">
                            <span style="font-size: 0.75rem; color: var(--text-secondary);">${comp.service}</span>
                            <span style="font-weight: 500;">${comp.component}</span>
                        </div>
                    </td>
                    <td style="font-weight: 600; color: var(--accent-secondary);">${comp.count}</td>
                    <td style="color: var(--text-secondary); font-size: 0.85rem;">${comp.unit}</td>
                    <td style="font-weight: 600; color: var(--text-primary);">${formatCurrency(comp.cost)}</td>
                `;
                usageTableBody.appendChild(tr);
            });
        }
    }

    function formatCurrency(value) {
        if (value === 'N/A*' || isNaN(value)) return value;
        return new Intl.NumberFormat('en-US', {
            style: 'currency',
            currency: 'USD',
        }).format(value);
    }

    function showLoader() { loader.classList.remove('hidden'); }
    function hideLoader() { loader.classList.add('hidden'); }
});

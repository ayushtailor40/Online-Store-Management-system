/**
 * Smart Online Store Management - Dashboard Charts & KPI Controller
 */

let charts = {};

document.addEventListener('DOMContentLoaded', () => {
    initDashboard();

    window.addEventListener('themeChanged', () => {
        updateChartThemeColors();
    });
});

function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        textColor: isDark ? '#9ca3af' : '#64748b',
        gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)',
        tooltipBg: isDark ? '#1f2937' : '#0f172a',
        tooltipText: '#ffffff'
    };
}

function formatCurrency(val) {
    return '$' + Number(val).toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}

function initDashboard() {
    // Setup filter event listeners
    const presetBtns = document.querySelectorAll('.btn-filter-preset');
    presetBtns.forEach(btn => {
        btn.addEventListener('click', (e) => {
            e.preventDefault();
            presetBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');
            
            const preset = btn.getAttribute('data-preset');
            const customDates = document.getElementById('custom-date-range-container');
            if (customDates) {
                customDates.style.display = preset === 'custom' ? 'flex' : 'none';
            }
            if (preset !== 'custom') {
                loadDashboardData();
            }
        });
    });

    const categorySelect = document.getElementById('dashboard-category-filter');
    if (categorySelect) {
        categorySelect.addEventListener('change', () => loadDashboardData());
    }

    const applyCustomBtn = document.getElementById('btn-apply-custom-date');
    if (applyCustomBtn) {
        applyCustomBtn.addEventListener('click', () => loadDashboardData());
    }

    // Initial fetch and charts setup
    loadDashboardData();
}

function loadDashboardData() {
    const activeBtn = document.querySelector('.btn-filter-preset.active');
    const preset = activeBtn ? activeBtn.getAttribute('data-preset') : 'all';
    const categorySelect = document.getElementById('dashboard-category-filter');
    const categoryId = categorySelect ? categorySelect.value : 'all';
    const startDate = document.getElementById('custom-start-date') ? document.getElementById('custom-start-date').value : '';
    const endDate = document.getElementById('custom-end-date') ? document.getElementById('custom-end-date').value : '';

    const params = new URLSearchParams({
        preset: preset,
        category_id: categoryId,
        start_date: startDate,
        end_date: endDate
    });

    fetch(`/api/dashboard/stats?${params.toString()}`)
        .then(res => res.json())
        .then(data => {
            updateKPICards(data.kpis);
            renderOrUpdateCharts(data.charts);
        })
        .catch(err => console.error("Error loading dashboard data:", err));
}

function updateKPICards(kpis) {
    if (!kpis) return;
    const revEl = document.getElementById('kpi-revenue');
    const profEl = document.getElementById('kpi-profit');
    const ordEl = document.getElementById('kpi-orders');
    const custEl = document.getElementById('kpi-customers');
    const prodEl = document.getElementById('kpi-products');
    const lowEl = document.getElementById('kpi-low-stock');
    const growthEl = document.getElementById('kpi-growth');

    if (revEl) revEl.innerText = formatCurrency(kpis.total_revenue);
    if (profEl) profEl.innerText = formatCurrency(kpis.total_profit);
    if (ordEl) ordEl.innerText = Number(kpis.total_orders).toLocaleString();
    if (custEl) custEl.innerText = Number(kpis.total_customers).toLocaleString();
    if (prodEl) prodEl.innerText = Number(kpis.total_products).toLocaleString();
    if (lowEl) lowEl.innerText = Number(kpis.low_stock_products).toLocaleString();

    if (growthEl) {
        const growth = Number(kpis.sales_growth_pct || 0);
        growthEl.className = 'trend-badge ' + (growth >= 0 ? 'trend-up' : 'trend-down');
        growthEl.innerHTML = `<i class="fa-solid fa-arrow-${growth >= 0 ? 'up' : 'down'}"></i> ${Math.abs(growth)}%`;
    }
}

function renderOrUpdateCharts(chartData) {
    const colors = getChartColors();

    // 1. Monthly Sales Trend (Line Chart)
    const trendCtx = document.getElementById('chart-monthly-trend');
    if (trendCtx) {
        if (charts.monthlyTrend) {
            charts.monthlyTrend.data.labels = chartData.monthly_trend.labels;
            charts.monthlyTrend.data.datasets[0].data = chartData.monthly_trend.revenues;
            charts.monthlyTrend.data.datasets[1].data = chartData.monthly_trend.profits;
            charts.monthlyTrend.update();
        } else {
            charts.monthlyTrend = new Chart(trendCtx, {
                type: 'line',
                data: {
                    labels: chartData.monthly_trend.labels,
                    datasets: [
                        {
                            label: 'Revenue ($)',
                            data: chartData.monthly_trend.revenues,
                            borderColor: '#3b82f6',
                            backgroundColor: 'rgba(59, 130, 246, 0.1)',
                            fill: true,
                            tension: 0.35,
                            borderWidth: 2.5
                        },
                        {
                            label: 'Gross Profit ($)',
                            data: chartData.monthly_trend.profits,
                            borderColor: '#10b981',
                            backgroundColor: 'rgba(16, 185, 129, 0.05)',
                            fill: true,
                            tension: 0.35,
                            borderWidth: 2
                        }
                    ]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'top', labels: { color: colors.textColor } },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.dataset.label}: ${formatCurrency(ctx.parsed.y)}`
                            }
                        }
                    },
                    scales: {
                        x: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor } },
                        y: {
                            grid: { color: colors.gridColor },
                            ticks: {
                                color: colors.textColor,
                                callback: val => '$' + Number(val).toLocaleString()
                            }
                        }
                    }
                }
            });
        }
    }

    // 2. Revenue by Category (Doughnut Chart)
    const catCtx = document.getElementById('chart-category-revenue');
    if (catCtx) {
        const palette = ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b', '#14b8a6'];
        if (charts.categoryRevenue) {
            charts.categoryRevenue.data.labels = chartData.category_revenue.labels;
            charts.categoryRevenue.data.datasets[0].data = chartData.category_revenue.data;
            charts.categoryRevenue.update();
        } else {
            charts.categoryRevenue = new Chart(catCtx, {
                type: 'doughnut',
                data: {
                    labels: chartData.category_revenue.labels,
                    datasets: [{
                        data: chartData.category_revenue.data,
                        backgroundColor: palette,
                        borderWidth: 2,
                        borderColor: document.documentElement.getAttribute('data-theme') === 'dark' ? '#111827' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: colors.textColor, boxWidth: 12 } },
                        tooltip: {
                            callbacks: {
                                label: ctx => `${ctx.label}: ${formatCurrency(ctx.parsed)}`
                            }
                        }
                    },
                    cutout: '65%'
                }
            });
        }
    }

    // 3. Top 10 Best-Selling Products (Horizontal Bar)
    const topCtx = document.getElementById('chart-top-products');
    if (topCtx) {
        if (charts.topProducts) {
            charts.topProducts.data.labels = chartData.top_products.labels;
            charts.topProducts.data.datasets[0].data = chartData.top_products.revenues;
            charts.topProducts.update();
        } else {
            charts.topProducts = new Chart(topCtx, {
                type: 'bar',
                data: {
                    labels: chartData.top_products.labels,
                    datasets: [{
                        label: 'Total Revenue ($)',
                        data: chartData.top_products.revenues,
                        backgroundColor: '#6366f1',
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: 'y',
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => `Revenue: ${formatCurrency(ctx.parsed.x)}`
                            }
                        }
                    },
                    scales: {
                        x: {
                            grid: { color: colors.gridColor },
                            ticks: {
                                color: colors.textColor,
                                callback: val => '$' + Number(val).toLocaleString()
                            }
                        },
                        y: { grid: { display: false }, ticks: { color: colors.textColor } }
                    }
                }
            });
        }
    }

    // 4. Profit by Product (Bar Chart)
    const profitCtx = document.getElementById('chart-profit-products');
    if (profitCtx) {
        if (charts.profitProducts) {
            charts.profitProducts.data.labels = chartData.profit_products.labels;
            charts.profitProducts.data.datasets[0].data = chartData.profit_products.profits;
            charts.profitProducts.update();
        } else {
            charts.profitProducts = new Chart(profitCtx, {
                type: 'bar',
                data: {
                    labels: chartData.profit_products.labels,
                    datasets: [{
                        label: 'Gross Profit ($)',
                        data: chartData.profit_products.profits,
                        backgroundColor: '#10b981',
                        borderRadius: 6
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { display: false },
                        tooltip: {
                            callbacks: {
                                label: ctx => `Profit: ${formatCurrency(ctx.parsed.y)}`
                            }
                        }
                    },
                    scales: {
                        x: { grid: { display: false }, ticks: { color: colors.textColor } },
                        y: {
                            grid: { color: colors.gridColor },
                            ticks: {
                                color: colors.textColor,
                                callback: val => '$' + Number(val).toLocaleString()
                            }
                        }
                    }
                }
            });
        }
    }

    // 5. Order Status Distribution (Doughnut Chart)
    const statusCtx = document.getElementById('chart-order-status');
    if (statusCtx) {
        const statusColors = {
            'Delivered': '#10b981',
            'Shipped': '#3b82f6',
            'Confirmed': '#6366f1',
            'Pending': '#f59e0b',
            'Cancelled': '#ef4444'
        };
        const bgColors = chartData.status_distribution.labels.map(l => statusColors[l] || '#94a3b8');

        if (charts.orderStatus) {
            charts.orderStatus.data.labels = chartData.status_distribution.labels;
            charts.orderStatus.data.datasets[0].data = chartData.status_distribution.data;
            charts.orderStatus.data.datasets[0].backgroundColor = bgColors;
            charts.orderStatus.update();
        } else {
            charts.orderStatus = new Chart(statusCtx, {
                type: 'doughnut',
                data: {
                    labels: chartData.status_distribution.labels,
                    datasets: [{
                        data: chartData.status_distribution.data,
                        backgroundColor: bgColors,
                        borderWidth: 2,
                        borderColor: document.documentElement.getAttribute('data-theme') === 'dark' ? '#111827' : '#ffffff'
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    plugins: {
                        legend: { position: 'bottom', labels: { color: colors.textColor, boxWidth: 12 } }
                    },
                    cutout: '60%'
                }
            });
        }
    }
}

function updateChartThemeColors() {
    const colors = getChartColors();
    Object.values(charts).forEach(chart => {
        if (chart.options.scales) {
            if (chart.options.scales.x) {
                if (chart.options.scales.x.ticks) chart.options.scales.x.ticks.color = colors.textColor;
                if (chart.options.scales.x.grid) chart.options.scales.x.grid.color = colors.gridColor;
            }
            if (chart.options.scales.y) {
                if (chart.options.scales.y.ticks) chart.options.scales.y.ticks.color = colors.textColor;
                if (chart.options.scales.y.grid) chart.options.scales.y.grid.color = colors.gridColor;
            }
        }
        if (chart.options.plugins && chart.options.plugins.legend) {
            chart.options.plugins.legend.labels.color = colors.textColor;
        }
        chart.update();
    });
}

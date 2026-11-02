/**
 * Advanced Analytics Page Charts Controller
 */

let analyticsCharts = {};

document.addEventListener('DOMContentLoaded', () => {
    initAnalyticsPage();

    window.addEventListener('themeChanged', () => {
        updateAnalyticsThemeColors();
    });
});

function getChartColors() {
    const isDark = document.documentElement.getAttribute('data-theme') === 'dark';
    return {
        textColor: isDark ? '#9ca3af' : '#64748b',
        gridColor: isDark ? 'rgba(255, 255, 255, 0.06)' : 'rgba(0, 0, 0, 0.05)'
    };
}

function initAnalyticsPage() {
    fetch('/analytics/api/charts')
        .then(res => res.json())
        .then(data => {
            renderAnalyticsCharts(data);
        })
        .catch(err => console.error("Error loading analytics charts:", err));
}

function renderAnalyticsCharts(data) {
    const colors = getChartColors();

    // 1. Sales & Profit Trend
    const salesCtx = document.getElementById('analytics-sales-trend-chart');
    if (salesCtx) {
        analyticsCharts.salesTrend = new Chart(salesCtx, {
            type: 'bar',
            data: {
                labels: data.monthly_trend.labels,
                datasets: [
                    {
                        label: 'Gross Revenue ($)',
                        data: data.monthly_trend.revenues,
                        backgroundColor: '#3b82f6',
                        borderRadius: 6
                    },
                    {
                        label: 'Gross Profit ($)',
                        data: data.monthly_trend.profits,
                        backgroundColor: '#10b981',
                        borderRadius: 6
                    }
                ]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { labels: { color: colors.textColor } }
                },
                scales: {
                    x: { grid: { color: colors.gridColor }, ticks: { color: colors.textColor } },
                    y: {
                        grid: { color: colors.gridColor },
                        ticks: {
                            color: colors.textColor,
                            callback: v => '$' + Number(v).toLocaleString()
                        }
                    }
                }
            }
        });
    }

    // 2. Category Share Doughnut
    const catCtx = document.getElementById('analytics-category-chart');
    if (catCtx) {
        analyticsCharts.category = new Chart(catCtx, {
            type: 'doughnut',
            data: {
                labels: data.category_revenue.labels,
                datasets: [{
                    data: data.category_revenue.data,
                    backgroundColor: ['#3b82f6', '#10b981', '#f59e0b', '#8b5cf6', '#ec4899', '#06b6d4', '#64748b', '#14b8a6'],
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
                cutout: '65%'
            }
        });
    }

    // 3. Top Products Horizontal Bar
    const topCtx = document.getElementById('analytics-top-products-chart');
    if (topCtx) {
        analyticsCharts.topProducts = new Chart(topCtx, {
            type: 'bar',
            data: {
                labels: data.top_products.labels,
                datasets: [{
                    label: 'Revenue ($)',
                    data: data.top_products.revenues,
                    backgroundColor: '#6366f1',
                    borderRadius: 6
                }]
            },
            options: {
                indexAxis: 'y',
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: { display: false }
                },
                scales: {
                    x: {
                        grid: { color: colors.gridColor },
                        ticks: {
                            color: colors.textColor,
                            callback: v => '$' + Number(v).toLocaleString()
                        }
                    },
                    y: { grid: { display: false }, ticks: { color: colors.textColor } }
                }
            }
        });
    }
}

function updateAnalyticsThemeColors() {
    const colors = getChartColors();
    Object.values(analyticsCharts).forEach(chart => {
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

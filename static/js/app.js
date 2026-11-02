/**
 * Smart Online Store Management & Data Analytics System
 * Global Application JavaScript
 */

document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    initSidebar();
    initToasts();
    initConfirmModals();
});

// --- Theme Management (Light / Dark Mode) ---
function initTheme() {
    const savedTheme = localStorage.getItem('app-theme') || 'light';
    setTheme(savedTheme);

    const themeToggleBtn = document.getElementById('theme-toggle-btn');
    if (themeToggleBtn) {
        themeToggleBtn.addEventListener('click', () => {
            const currentTheme = document.documentElement.getAttribute('data-theme') || 'light';
            const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
            setTheme(newTheme);
            localStorage.setItem('app-theme', newTheme);
            
            // Dispatch event for Chart.js instances to re-render with appropriate theme colors
            window.dispatchEvent(new CustomEvent('themeChanged', { detail: { theme: newTheme } }));
        });
    }
}

function setTheme(theme) {
    document.documentElement.setAttribute('data-theme', theme);
    const themeIcon = document.getElementById('theme-toggle-icon');
    if (themeIcon) {
        if (theme === 'dark') {
            themeIcon.className = 'fa-solid fa-sun';
            themeIcon.title = 'Switch to Light Mode';
        } else {
            themeIcon.className = 'fa-solid fa-moon';
            themeIcon.title = 'Switch to Dark Mode';
        }
    }
}

// --- Responsive Sidebar Toggle ---
function initSidebar() {
    const sidebar = document.getElementById('app-sidebar');
    const menuBtn = document.getElementById('menu-toggle-btn');
    const backdrop = document.getElementById('sidebar-backdrop');

    if (menuBtn && sidebar) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            if (backdrop) backdrop.classList.toggle('active');
        });
    }

    if (backdrop && sidebar) {
        backdrop.addEventListener('click', () => {
            sidebar.classList.remove('open');
            backdrop.classList.remove('active');
        });
    }
}

// --- Flash Toast Notifications ---
function initToasts() {
    const toasts = document.querySelectorAll('.toast');
    toasts.forEach(toast => {
        // Auto-dismiss after 5 seconds
        setTimeout(() => {
            toast.style.opacity = '0';
            setTimeout(() => toast.remove(), 300);
        }, 5000);

        const closeBtn = toast.querySelector('.toast-close');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                toast.remove();
            });
        }
    });
}

// --- Confirmation Modals for Destructive Actions ---
function initConfirmModals() {
    document.addEventListener('submit', (e) => {
        const form = e.target;
        const confirmMsg = form.getAttribute('data-confirm');
        if (confirmMsg) {
            if (!confirm(confirmMsg)) {
                e.preventDefault();
            }
        }
    });
}

// --- Generic Modal Helpers ---
window.openModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.add('active');
    }
};

window.closeModal = function(modalId) {
    const modal = document.getElementById(modalId);
    if (modal) {
        modal.classList.remove('active');
    }
};

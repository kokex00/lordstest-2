// Dashboard JavaScript functionality

class DashboardManager {
    constructor() {
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.startAutoRefresh();
        this.initializeTooltips();
    }

    setupEventListeners() {
        // Auto-refresh toggle
        const autoRefreshToggle = document.getElementById('auto-refresh-toggle');
        if (autoRefreshToggle) {
            autoRefreshToggle.addEventListener('change', (e) => {
                if (e.target.checked) {
                    this.startAutoRefresh();
                } else {
                    this.stopAutoRefresh();
                }
            });
        }

        // Manual refresh button
        const refreshBtn = document.getElementById('manual-refresh');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', () => {
                this.refreshData();
            });
        }

        // Search functionality
        const searchInput = document.getElementById('search-input');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterData(e.target.value);
            });
        }
    }

    initializeTooltips() {
        // Initialize Bootstrap tooltips
        const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
        tooltipTriggerList.map(function (tooltipTriggerEl) {
            return new bootstrap.Tooltip(tooltipTriggerEl);
        });
    }

    startAutoRefresh() {
        this.autoRefreshInterval = setInterval(() => {
            this.refreshData();
        }, 30000); // Refresh every 30 seconds
    }

    stopAutoRefresh() {
        if (this.autoRefreshInterval) {
            clearInterval(this.autoRefreshInterval);
        }
    }

    async refreshData() {
        try {
            const refreshBtn = document.getElementById('manual-refresh');
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-spinner fa-spin me-1"></i>Refreshing...';
                refreshBtn.disabled = true;
            }

            // Refresh statistics
            await this.updateStatistics();
            
            // Refresh charts if they exist
            if (typeof updateCharts === 'function') {
                updateCharts();
            }

            // Show success message
            this.showNotification('Data refreshed successfully', 'success');

        } catch (error) {
            console.error('Error refreshing data:', error);
            this.showNotification('Failed to refresh data', 'error');
        } finally {
            const refreshBtn = document.getElementById('manual-refresh');
            if (refreshBtn) {
                refreshBtn.innerHTML = '<i class="fas fa-sync-alt me-1"></i>Refresh';
                refreshBtn.disabled = false;
            }
        }
    }

    async updateStatistics() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();

            // Update stat cards
            const statsElements = {
                'servers': document.getElementById('stat-servers'),
                'matches': document.getElementById('stat-matches'),
                'active_matches': document.getElementById('stat-active-matches'),
                'logs': document.getElementById('stat-logs')
            };

            Object.entries(statsElements).forEach(([key, element]) => {
                if (element && stats[key] !== undefined) {
                    this.animateNumber(element, parseInt(element.textContent) || 0, stats[key]);
                }
            });

        } catch (error) {
            console.error('Error updating statistics:', error);
        }
    }

    animateNumber(element, start, end) {
        const duration = 1000;
        const range = end - start;
        const increment = Math.ceil(range / (duration / 16));
        let current = start;

        const timer = setInterval(() => {
            current += increment;
            if ((increment > 0 && current >= end) || (increment < 0 && current <= end)) {
                current = end;
                clearInterval(timer);
            }
            element.textContent = current.toLocaleString();
        }, 16);
    }

    filterData(searchTerm) {
        const tableRows = document.querySelectorAll('.filterable-table tbody tr');
        
        tableRows.forEach(row => {
            const text = row.textContent.toLowerCase();
            const matches = text.includes(searchTerm.toLowerCase());
            row.style.display = matches ? '' : 'none';
        });

        // Update visible count
        const visibleRows = Array.from(tableRows).filter(row => row.style.display !== 'none');
        const countElement = document.getElementById('filtered-count');
        if (countElement) {
            countElement.textContent = `${visibleRows.length} of ${tableRows.length}`;
        }
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `alert alert-${type === 'error' ? 'danger' : type} alert-dismissible fade show position-fixed`;
        notification.style.top = '20px';
        notification.style.right = '20px';
        notification.style.zIndex = '9999';
        notification.style.minWidth = '300px';

        notification.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="fas fa-${type === 'success' ? 'check-circle' : type === 'error' ? 'exclamation-triangle' : 'info-circle'} me-2"></i>
                <span>${message}</span>
                <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
            </div>
        `;

        document.body.appendChild(notification);

        // Auto-remove after 5 seconds
        setTimeout(() => {
            if (notification.parentNode) {
                notification.remove();
            }
        }, 5000);
    }

    formatTimestamp(timestamp) {
        const date = new Date(timestamp);
        const now = new Date();
        const diff = now - date;

        // Less than a minute
        if (diff < 60000) {
            return 'Just now';
        }

        // Less than an hour
        if (diff < 3600000) {
            const minutes = Math.floor(diff / 60000);
            return `${minutes} minute${minutes > 1 ? 's' : ''} ago`;
        }

        // Less than a day
        if (diff < 86400000) {
            const hours = Math.floor(diff / 3600000);
            return `${hours} hour${hours > 1 ? 's' : ''} ago`;
        }

        // More than a day
        return date.toLocaleDateString();
    }

    // Utility method for API calls
    async apiCall(endpoint, options = {}) {
        try {
            const response = await fetch(endpoint, {
                headers: {
                    'Content-Type': 'application/json',
                    ...options.headers
                },
                ...options
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            return await response.json();
        } catch (error) {
            console.error('API call failed:', error);
            throw error;
        }
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    window.dashboardManager = new DashboardManager();
});

// Global utility functions
window.formatNumber = function(num) {
    if (num >= 1000000) {
        return (num / 1000000).toFixed(1) + 'M';
    }
    if (num >= 1000) {
        return (num / 1000).toFixed(1) + 'K';
    }
    return num.toString();
};

window.copyToClipboard = function(text) {
    navigator.clipboard.writeText(text).then(() => {
        window.dashboardManager.showNotification('Copied to clipboard', 'success');
    }).catch(() => {
        window.dashboardManager.showNotification('Failed to copy', 'error');
    });
};

// Handle page visibility change to pause/resume auto-refresh
document.addEventListener('visibilitychange', function() {
    if (window.dashboardManager) {
        if (document.hidden) {
            window.dashboardManager.stopAutoRefresh();
        } else {
            window.dashboardManager.startAutoRefresh();
        }
    }
});

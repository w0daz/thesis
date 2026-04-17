/**
 * Common utilities and functions shared across all pages
 * Now includes  custom toast notifications
 */

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// API BASE URL
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

const API_BASE = window.location.origin;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// API WRAPPER FUNCTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function apiGet(endpoint) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`);
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API GET ${endpoint} failed:`, error);
        throw error;
    }
}

async function apiPost(endpoint, data) {
    try {
        const response = await fetch(`${API_BASE}${endpoint}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(data)
        });
        if (!response.ok) {
            throw new Error(`HTTP ${response.status}: ${response.statusText}`);
        }
        return await response.json();
    } catch (error) {
        console.error(`API POST ${endpoint} failed:`, error);
        throw error;
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CONNECTION STATUS MANAGEMENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function updateConnectionStatus(connected) {
    const statusBadge = document.getElementById('connection-status');
    if (!statusBadge) return;
    
    const statusDot = statusBadge.querySelector('.status-dot');
    const statusText = statusBadge.querySelector('.status-text');
    
    if (connected) {
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Connected';
        statusText.style.color = '';
    } else {
        statusDot.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
        statusText.style.color = '#f44336';
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// ACTIVE NAV LINK HIGHLIGHTING
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function setActiveNavLink() {
    const currentPath = window.location.pathname;
    const navLinks = document.querySelectorAll('.nav-link');
    
    navLinks.forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        
        if (
            (currentPath === '/' && href === '/') ||
            (currentPath !== '/' && href !== '/' && currentPath.startsWith(href))
        ) {
            link.classList.add('active');
        }
    });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// NOTIFICATION SYSTEM - BEAUTIFUL TOAST NOTIFICATIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

let notificationSettings = {
    enabled: true
};

// Initialize notification settings from localStorage
function initNotificationSettings() {
    try {
        const settings = JSON.parse(localStorage.getItem('notificationSettings') || '{}');
        notificationSettings = {
            enabled: settings.notification_enabled !== false
        };
    } catch (e) {
        console.log('Using default notification settings');
    }
}

// Update notification settings from API
async function syncNotificationSettings() {
    try {
        const settings = await apiGet('/api/settings');
        notificationSettings.enabled = settings.notification_enabled !== false;
        localStorage.setItem('notificationSettings', JSON.stringify(settings));
    } catch (error) {
        console.log('Could not sync notification settings');
    }
}

// Create notification styles if not already in document
function ensureNotificationStyles() {
    if (document.getElementById('notification-styles')) return;
    
    const style = document.createElement('style');
    style.id = 'notification-styles';
    style.textContent = `
        @keyframes slideInUp {
            from {
                transform: translateY(400px);
                opacity: 0;
            }
            to {
                transform: translateY(0);
                opacity: 1;
            }
        }

        @keyframes slideOutDown {
            from {
                transform: translateY(0);
                opacity: 1;
            }
            to {
                transform: translateY(400px);
                opacity: 0;
            }
        }

        @keyframes slideInRight {
            from {
                transform: translateX(400px);
                opacity: 0;
            }
            to {
                transform: translateX(0);
                opacity: 1;
            }
        }

        @keyframes slideOutRight {
            from {
                transform: translateX(0);
                opacity: 1;
            }
            to {
                transform: translateX(400px);
                opacity: 0;
            }
        }

        #notification-container {
            position: fixed;
            bottom: 20px;
            right: 20px;
            z-index: 9999;
            max-width: 380px;
            display: flex;
            flex-direction: column;
            gap: 0.75rem;
        }

        .notification {
            background: white;
            padding: 1rem 1.25rem;
            border-radius: 12px;
            box-shadow: 0 8px 32px rgba(0,0,0,0.15);
            border-left: 4px solid #667eea;
            animation: slideInRight 0.35s cubic-bezier(0.34, 1.56, 0.64, 1);
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            color: #2c3e50;
            font-weight: 500;
            font-size: 0.95rem;
            line-height: 1.5;
            display: flex;
            align-items: flex-start;
            gap: 0.75rem;
            min-width: 320px;
        }

        .notification.hidden {
            animation: slideOutRight 0.35s cubic-bezier(0.34, 1.56, 0.64, 1) forwards;
        }

        .notification-icon {
            font-size: 1.25rem;
            flex-shrink: 0;
            margin-top: 2px;
        }

        .notification-content {
            flex: 1;
        }

        .notification-title {
            font-weight: 600;
            margin-bottom: 0.25rem;
            color: #2c3e50;
        }

        .notification-message {
            opacity: 0.85;
            font-size: 0.9rem;
        }

        /* Success Notification */
        .notification.notification-success {
            border-left-color: #4CAF50;
            background: linear-gradient(135deg, #f1f8f4 0%, #ffffff 100%);
        }

        .notification.notification-success .notification-icon {
            color: #4CAF50;
        }

        .notification.notification-success .notification-title {
            color: #2e7d32;
        }

        /* Error Notification */
        .notification.notification-error {
            border-left-color: #f44336;
            background: linear-gradient(135deg, #ffebee 0%, #ffffff 100%);
        }

        .notification.notification-error .notification-icon {
            color: #f44336;
        }

        .notification.notification-error .notification-title {
            color: #c62828;
        }

        /* Warning Notification */
        .notification.notification-warning {
            border-left-color: #ff9800;
            background: linear-gradient(135deg, #fff3e0 0%, #ffffff 100%);
        }

        .notification.notification-warning .notification-icon {
            color: #ff9800;
        }

        .notification.notification-warning .notification-title {
            color: #f57c00;
        }

        /* Info Notification */
        .notification.notification-info {
            border-left-color: #2196F3;
            background: linear-gradient(135deg, #e3f2fd 0%, #ffffff 100%);
        }

        .notification.notification-info .notification-icon {
            color: #2196F3;
        }

        .notification.notification-info .notification-title {
            color: #1565c0;
        }

        /* Alert Notification (for anomalies) */
        .notification.notification-alert {
            border-left-color: #667eea;
            background: linear-gradient(135deg, #f0f1ff 0%, #ffffff 100%);
        }

        .notification.notification-alert .notification-icon {
            color: #667eea;
            font-size: 1.5rem;
        }

        .notification.notification-alert .notification-title {
            color: #667eea;
            font-size: 1rem;
        }

        .notification.notification-alert .notification-message {
            color: #764ba2;
            font-weight: 500;
        }

        @media (max-width: 768px) {
            #notification-container {
                right: 10px;
                bottom: 10px;
                left: 10px;
                max-width: none;
            }

            .notification {
                min-width: unset;
                padding: 0.9rem 1rem;
                font-size: 0.9rem;
            }
        }
    `;
    document.head.appendChild(style);
}

function showNotification(message, type = 'info', duration = 5000) {
    // Respect notification settings (unless it's an alert)
    if (!notificationSettings.enabled && type !== 'alert') {
        console.log('ℹ️ Notifications disabled by user');
        return;
    }

    ensureNotificationStyles();

    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;

    const icons = {
        success: '✅',
        error: '❌',
        warning: '⚠️',
        info: 'ℹ️',
        alert: '🔔'
    };

    const icon = icons[type] || icons.info;

    notification.innerHTML = `
        <div class="notification-icon">${icon}</div>
        <div class="notification-content">
            <div class="notification-message">${message}</div>
        </div>
    `;

    container.appendChild(notification);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.add('hidden');
            setTimeout(() => notification.remove(), 350);
        }, duration);
    }

    return notification;
}

// Alert notification (for important events like new anomalies) - stays longer
function showAlertNotification(title, message, duration = 8000) {
    // Check notification setting
    if (!notificationSettings.enabled) {
        console.log('ℹ️ Alert notifications disabled by user');
        return;
    }

    ensureNotificationStyles();

    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    notification.className = 'notification notification-alert';

    notification.innerHTML = `
        <div class="notification-icon">🔔</div>
        <div class="notification-content">
            <div class="notification-title">${title}</div>
            <div class="notification-message">${message}</div>
        </div>
    `;

    container.appendChild(notification);

    // Auto-remove after duration
    if (duration > 0) {
        setTimeout(() => {
            notification.classList.add('hidden');
            setTimeout(() => notification.remove(), 350);
        }, duration);
    }

    return notification;
}

function showConfirmNotification(message, onConfirm, onCancel) {
    ensureNotificationStyles();

    let container = document.getElementById('notification-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'notification-container';
        document.body.appendChild(container);
    }

    const notification = document.createElement('div');
    notification.className = 'notification notification-warning';

    notification.innerHTML = `
        <div class="notification-icon">⚠️</div>
        <div class="notification-content">
            <div class="notification-title">Confirm Action</div>
            <div class="notification-message">${message}</div>
            <div style="margin-top: 0.75rem; display: flex; gap: 0.5rem;">
                <button class="btn" id="notif-confirm-btn" style="padding: 0.4rem 0.8rem; font-size: 0.85rem;">Confirm</button>
                <button class="btn" id="notif-cancel-btn" style="padding: 0.4rem 0.8rem; font-size: 0.85rem; background:#7f8c8d;">Cancel</button>
            </div>
        </div>
    `;

    container.appendChild(notification);

    notification.querySelector('#notif-confirm-btn')?.addEventListener('click', () => {
        notification.classList.add('hidden');
        setTimeout(() => notification.remove(), 350);
        onConfirm?.();
    });

    notification.querySelector('#notif-cancel-btn')?.addEventListener('click', () => {
        notification.classList.add('hidden');
        setTimeout(() => notification.remove(), 350);
        onCancel?.();
    });

    return notification;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// FORMAT HELPERS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function formatDateTime(isoString) {
    return new Date(isoString).toLocaleString();
}

function formatTime(isoString) {
    return new Date(isoString).toLocaleTimeString();
}

function formatPower(kw, decimals = 3) {
    return `${kw.toFixed(decimals)} kW`;
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INITIALIZE ON PAGE LOAD
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

document.addEventListener('DOMContentLoaded', () => {
    setActiveNavLink();
    initNotificationSettings();
    syncNotificationSettings();
    console.log('✅ Common utilities loaded');
});
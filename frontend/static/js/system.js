/**
 * System Page - Status, Logs, and Diagnostics
 * ✅ Now uses beautiful custom notifications from common.js
 */

let systemInterval = null;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILITY FUNCTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function updateConnectionStatus(connected) {
    const statusBadge = document.getElementById('connection-status');
    if (!statusBadge) return;
    
    const statusDot = statusBadge.querySelector('.status-dot');
    const statusText = statusBadge.querySelector('.status-text');
    
    if (connected) {
        statusDot.classList.remove('disconnected');
        statusText.textContent = 'Connected';
    } else {
        statusDot.classList.add('disconnected');
        statusText.textContent = 'Disconnected';
    }
}

function formatTimeAgo(dateString) {
    /**
     * Format a timestamp as scientific notation
     * Format: DD/MM/YYYY, HH:MM:SS
     */
    try {
        const date = new Date(dateString);
        
        // Pad numbers with leading zeros
        const pad = (num) => String(num).padStart(2, '0');
        
        const day = pad(date.getDate());
        const month = pad(date.getMonth() + 1);
        const year = date.getFullYear();
        const hours = pad(date.getHours());
        const minutes = pad(date.getMinutes());
        const seconds = pad(date.getSeconds());
        
        return `${day}/${month}/${year}, ${hours}:${minutes}:${seconds}`;
    } catch {
        return 'Unknown';
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SYSTEM STATUS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function updateSystemStatus() {
    try {
        const response = await fetch('/api/health');
        
        if (!response.ok) {
            updateConnectionStatus(false);
            document.getElementById('api-status').textContent = '❌ Error';
            document.getElementById('api-status').className = 'status-value danger';
            return;
        }
        
        const health = await response.json();
        updateConnectionStatus(true);
        
        document.getElementById('api-status').textContent = '✅ Healthy';
        document.getElementById('api-status').className = 'status-value success';
        
        const lastCheck = new Date(health.timestamp);
        document.getElementById('last-check').textContent = lastCheck.toLocaleTimeString();
        
    } catch (error) {
        console.error('Error fetching system status:', error);
        updateConnectionStatus(false);
        document.getElementById('api-status').textContent = '❌ Error';
        document.getElementById('api-status').className = 'status-value danger';
    }
}

async function updateLastSpike() {
    /**
     * Fetch recent alerts and determine the latest spike by comparing timestamps.
     * Uses created_at when available, falls back to timestamp.
     */
    try {
        const response = await fetch('/api/alerts?limit=200');
        if (!response.ok) {
            document.getElementById('last-spike').textContent = 'Never';
            return;
        }

        const alerts = await response.json();
        const lastSpikeElement = document.getElementById('last-spike');
        if (!alerts || alerts.length === 0) {
            lastSpikeElement.textContent = 'Never';
            return;
        }

        let latest = null;
        for (const a of alerts) {
            const cand = a.created_at || a.timestamp;
            if (!cand) continue;
            const d = new Date(cand);
            if (isNaN(d.getTime())) continue;
            if (latest === null || d.getTime() > latest.getTime()) latest = d;
        }

        if (!latest) {
            lastSpikeElement.textContent = 'Unknown';
            return;
        }

        lastSpikeElement.textContent = formatTimeAgo(latest.toISOString());
    } catch (error) {
        console.error('Error fetching last spike:', error);
        document.getElementById('last-spike').textContent = 'Error loading';
    }
}

async function updateSystemInfo() {
    try {
        const response = await fetch('/api/statistics');
        
        if (!response.ok) {
            console.error('Statistics API Error:', response.status);
            return;
        }
        
        const data = await response.json();
        
        document.getElementById('total-readings').textContent = 
            data.total_readings.toLocaleString();
        
        document.getElementById('total-alerts').textContent = data.alerts || 0;
        
        const currentResponse = await fetch('/api/current');
        if (currentResponse.ok) {
            const currentData = await currentResponse.json();
            if (currentData.buffer_size) {
                const hours = (currentData.buffer_size / 60).toFixed(1);
                document.getElementById('buffer-size').textContent = `${hours} hours`;
            }
        }
        
        await updateLastSpike();
        
    } catch (error) {
        console.error('Error updating system info:', error);
    }
}

async function updateSchedulerStatus() {
    try {
        const response = await fetch('/api/scheduler/status');
        
        if (response.ok) {
            const data = await response.json();
            
            document.getElementById('scheduler-status').textContent = 
                data.running ? '✅ Running' : '❌ Stopped';
            document.getElementById('scheduler-status').className = 
                data.running ? 'status-value success' : 'status-value danger';
            
            if (data.jobs) {
                const jobsList = document.getElementById('jobs-list');
                jobsList.innerHTML = data.jobs.map(job => `
                    <div class="info-list">
                        <li>
                            <span class="label">${job.name || job.id}</span>
                            <span class="value">Next: ${new Date(job.next_run).toLocaleString()}</span>
                        </li>
                    </div>
                `).join('');
            }
        } else {
            document.getElementById('scheduler-status').textContent = 'ℹ️ Not Available';
            document.getElementById('scheduler-status').className = 'status-value';
        }
        
    } catch (error) {
        console.log('Scheduler status endpoint not available');
        document.getElementById('scheduler-status').textContent = 'ℹ️ Not Available';
        document.getElementById('scheduler-status').className = 'status-value';
    }
}

async function runDetection() {
    let pendingToast = null;

    try {
        if (typeof showNotification === 'function') {
            pendingToast = showNotification('🔍 Running anomaly detection...', 'info', 0);
        }
        
        const response = await fetch('/api/run-detection', {
            method: 'POST'
        });
        
        if (!response.ok) {
            throw new Error('Detection failed');
        }
        
        const result = await response.json();
        
        if (pendingToast) {
            pendingToast.classList.add('hidden');
            setTimeout(() => pendingToast.remove(), 350);
        }
        
        if (typeof showNotification === 'function') {
            showNotification(`Detection complete! Found ${result.alerts || 0} anomalies`, 'success');
        }
        
        updateSystemInfo();
        addLogEntry('info', `Detection complete: ${result.alerts || 0} anomalies found`);
        
    } catch (error) {
        if (pendingToast) {
            pendingToast.classList.add('hidden');
            setTimeout(() => pendingToast.remove(), 350);
        }
        if (typeof showNotification === 'function') {
            showNotification('Detection failed. Check console for details', 'error');
        }
        console.error('Detection error:', error);
        addLogEntry('error', 'Detection failed');
    }
}

async function recalculateBaseline() {
    try {
        if (typeof showNotification === 'function') {
            showNotification('📊 Recalculating baseline...', 'info');
        }
        
        const response = await fetch('/api/baseline?recalculate=true');
        
        if (!response.ok) {
            throw new Error('Baseline recalculation failed');
        }
        
        if (typeof showNotification === 'function') {
            showNotification('Baseline recalculated successfully', 'success');
        }
        
        addLogEntry('info', 'Baseline recalculated successfully');
        
    } catch (error) {
        if (typeof showNotification === 'function') {
            showNotification('Failed to recalculate baseline', 'error');
        }
        console.error('Baseline error:', error);
        addLogEntry('error', 'Baseline recalculation failed');
    }
}

async function clearAlerts() {
    if (typeof showConfirmNotification !== 'function') return;

    showConfirmNotification(
        'Are you sure you want to clear all alert history? This cannot be undone.',
        async () => {
            try {
                showNotification?.('🗑️ Clearing alerts...', 'info');

                const response = await fetch('/api/alerts', { method: 'DELETE' });
                if (!response.ok) throw new Error('Failed to clear alerts');

                const result = await response.json();
                showNotification?.(`Successfully cleared ${result.cleared_count} alerts`, 'success');

                updateSystemInfo();
                addLogEntry('info', `Cleared ${result.cleared_count} alerts`);
            } catch (error) {
                showNotification?.('Failed to clear alerts', 'error');
                console.error('Clear alerts error:', error);
                addLogEntry('error', 'Failed to clear alerts');
            }
        },
        () => {
            showNotification?.('Clear alerts canceled', 'warning');
        }
    );
}

function addLogEntry(level, message) {
    const logContainer = document.getElementById('log-container');
    const now = new Date();
    const timeStr = now.toLocaleTimeString();
    
    const entry = document.createElement('div');
    entry.className = 'log-entry';
    entry.innerHTML = `
        <span class="log-time">[${timeStr}]</span>
        <span class="log-level-${level}">[${level.toUpperCase()}]</span>
        ${message}
    `;
    
    logContainer.appendChild(entry);
    
    while (logContainer.children.length > 50) {
        logContainer.removeChild(logContainer.firstChild);
    }
    
    logContainer.scrollTop = logContainer.scrollHeight;
}

function updateAll() {
    updateSystemStatus();
    updateSystemInfo();
    updateSchedulerStatus();
    addLogEntry('info', 'System status refreshed');
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INITIALIZATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

document.addEventListener('DOMContentLoaded', () => {
    console.log('🖥️ System page initializing...');
    
    updateAll();
    
    systemInterval = setInterval(updateAll, 10000);
    
    document.getElementById('run-detection-btn')?.addEventListener('click', runDetection);
    document.getElementById('recalculate-baseline-btn')?.addEventListener('click', recalculateBaseline);
    document.getElementById('clear-alerts-btn')?.addEventListener('click', clearAlerts);
    document.getElementById('refresh-logs-btn')?.addEventListener('click', () => {
        addLogEntry('info', 'Manual refresh triggered');
        updateAll();
    });
    
    addLogEntry('info', 'System monitor initialized');
    addLogEntry('info', 'Auto-refresh enabled (10s interval)');
    
    console.log('✅ System page initialized!');
});

window.addEventListener('beforeunload', () => {
    if (systemInterval) clearInterval(systemInterval);
});
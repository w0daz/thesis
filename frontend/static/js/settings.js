/**
 * Settings Page - System Configuration
 * ✅ Updated to match functional backend settings
 */

let originalSettings = {};
let hasUnsavedChanges = false;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILITY FUNCTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function showSettingsStatus(message, type) {
    if (typeof showNotification === 'function') {
        const toastType =
            type === 'error' ? 'error' :
            type === 'warning' ? 'warning' :
            'success';

        showNotification(message, toastType);
        return;
    }

    // Fallback (if common.js not loaded)
    const statusDiv = document.getElementById('settings-status');
    statusDiv.textContent = message;
    statusDiv.className = `settings-status ${type}`;
    statusDiv.style.display = 'block';
    
    setTimeout(() => {
        statusDiv.style.display = 'none';
    }, 5000);
}

function updateSaveButton() {
    const saveBtn = document.getElementById('save-settings-btn');
    if (hasUnsavedChanges) {
        saveBtn.style.display = 'block';
    } else {
        saveBtn.style.display = 'none';
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// SETTINGS MANAGEMENT
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function loadSettings() {
    try {
        const response = await fetch('/api/settings');
        if (!response.ok) {
            console.error('Failed to load settings');
            return;
        }
        
        const settings = await response.json();
        
        // Store original settings
        originalSettings = {...settings};
        
        // Populate form with functional settings
        document.getElementById('sample-rate').value = settings.sample_rate_seconds || 60;
        document.getElementById('buffer-hours').value = settings.buffer_hours || 24;
        document.getElementById('detection-frequency').value = settings.detection_frequency_hours || 1;
        document.getElementById('model-sensitivity').value = settings.model_sensitivity || 0.03;
        document.getElementById('sensitivity-value').textContent = (settings.model_sensitivity || 0.03).toFixed(2);
        document.getElementById('notifications-enabled').checked = settings.notification_enabled !== false;
        
        hasUnsavedChanges = false;
        updateSaveButton();
        
        console.log('✅ Settings loaded');
        
    } catch (error) {
        console.error('Error loading settings:', error);
        showSettingsStatus('❌ Failed to load settings', 'error');
    }
}

async function saveSettings() {
    try {
        const settings = {
            sample_rate_seconds: parseInt(document.getElementById('sample-rate').value),
            buffer_hours: parseInt(document.getElementById('buffer-hours').value),
            detection_frequency_hours: parseFloat(document.getElementById('detection-frequency').value),
            model_sensitivity: parseFloat(document.getElementById('model-sensitivity').value),
            notification_enabled: document.getElementById('notifications-enabled').checked
        };
        
        const response = await fetch('/api/settings', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Failed to save settings');
        }
        
        const data = await response.json();
        
        // Update original settings
        originalSettings = {...data};
        hasUnsavedChanges = false;
        updateSaveButton();
        
        // Show warning if detection frequency changed
        if (data.warning) {
            showSettingsStatus(`⚠️ ${data.warning}`, 'warning');
        } else {
            showSettingsStatus('✅ Settings saved successfully!', 'success');
        }
        
        console.log('✅ Settings saved:', data);
        
    } catch (error) {
        console.error('Error saving settings:', error);
        showSettingsStatus('❌ Failed to save settings. Please try again.', 'error');
    }
}

function resetSettings() {
    if (typeof showConfirmNotification !== 'function') return;

    showConfirmNotification(
        'Reset all settings to defaults? This will overwrite current values.',
        () => {
            // Default values
            document.getElementById('sample-rate').value = 60;
            document.getElementById('buffer-hours').value = 24;
            document.getElementById('detection-frequency').value = 1;
            document.getElementById('model-sensitivity').value = 0.03;
            document.getElementById('sensitivity-value').textContent = '0.03';
            document.getElementById('notifications-enabled').checked = true;
            
            hasUnsavedChanges = true;
            updateSaveButton();
            
            showSettingsStatus('⚠️ Settings reset to defaults. Click "Apply Settings" to save.', 'warning');
        },
        () => {
            showSettingsStatus('Reset canceled.', 'warning');
        }
    );
}

function checkForChanges() {
    const current = {
        sample_rate_seconds: parseInt(document.getElementById('sample-rate').value),
        buffer_hours: parseInt(document.getElementById('buffer-hours').value),
        detection_frequency_hours: parseFloat(document.getElementById('detection-frequency').value),
        model_sensitivity: parseFloat(document.getElementById('model-sensitivity').value),
        notification_enabled: document.getElementById('notifications-enabled').checked
    };
    
    // Check each setting
    Object.keys(current).forEach(key => {
        const inputId = key.replace(/_/g, '-');
        const element = document.getElementById(inputId);
        if (element) {
            const settingItem = element.closest('.setting-item');
            if (settingItem && current[key] !== originalSettings[key]) {
                settingItem.classList.add('changed');
            } else if (settingItem) {
                settingItem.classList.remove('changed');
            }
        }
    });
    
    hasUnsavedChanges = JSON.stringify(current) !== JSON.stringify(originalSettings);
    updateSaveButton();
}

function initializeSettingsListeners() {
    // Model sensitivity slider
    const sensitivitySlider = document.getElementById('model-sensitivity');
    const sensitivityValue = document.getElementById('sensitivity-value');
    if (sensitivitySlider) {
        sensitivitySlider.addEventListener('input', (e) => {
            sensitivityValue.textContent = parseFloat(e.target.value).toFixed(2);
            checkForChanges();
        });
    }
    
    // All input changes
    const inputs = [
        'sample-rate',
        'buffer-hours',
        'detection-frequency',
        'notifications-enabled'
    ];
    
    inputs.forEach(id => {
        const element = document.getElementById(id);
        if (element) {
            element.addEventListener('change', checkForChanges);
        }
    });
    
    // Buttons
    document.getElementById('apply-settings-btn')?.addEventListener('click', saveSettings);
    document.getElementById('save-settings-btn')?.addEventListener('click', saveSettings);
    document.getElementById('reset-settings-btn')?.addEventListener('click', resetSettings);
    
    console.log('✅ Settings listeners initialized');
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INITIALIZATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

document.addEventListener('DOMContentLoaded', () => {
    console.log('⚙️ Settings page initializing...');
    
    initializeSettingsListeners();
    loadSettings();
    
    console.log('✅ Settings initialized!');
});
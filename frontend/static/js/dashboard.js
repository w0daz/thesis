/**
 * Dashboard Page - Main Power Monitoring
 * ✅ With Custom Beautiful Notifications System
 */

let powerChart = null;
let updateInterval = null;
let currentTimeRange = 6;
let allAlerts = [];
let lastAlertId = 0;

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILITY
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function updateConnectionStatus(connected) {
  const badge = document.getElementById("connection-status");
  if (!badge) return;

  badge.classList.toggle("disconnected", !connected);
  const statusText = badge.querySelector(".status-text");
  if (statusText) {
    statusText.textContent = connected ? "Connected" : "Disconnected";
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CHART
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function initPowerChart() {
  const canvas = document.getElementById("powerChart");
  if (!canvas) return;

  powerChart = new Chart(canvas.getContext("2d"), {
    type: "line",
    data: {
      datasets: [
        {
          label: "Power Consumption (kW)",
          data: [],
          borderColor: "#667eea",
          backgroundColor: "rgba(102,126,234,0.1)",
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: { intersect: false, mode: "index" },
      scales: {
        x: { type: "time", time: { unit: "minute" } },
        y: { beginAtZero: true },
      },
    },
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DATA UPDATES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function updateCurrentPower() {
  try {
    const res = await fetch("/api/current");
    if (!res.ok) throw new Error();

    const d = await res.json();
    updateConnectionStatus(true);

    const powerValue = document.querySelector("#current-power .value");
    if (powerValue) {
      powerValue.textContent = d.power_kw.toFixed(3);
    }

    const voltageEl = document.getElementById("voltage");
    if (voltageEl) {
      voltageEl.textContent = `${d.voltage.toFixed(1)} V`;
    }

    const currentEl = document.getElementById("current");
    if (currentEl) {
      currentEl.textContent = `${d.current_a.toFixed(2)} A`;
    }

    const baselineEl = document.getElementById("baseline");
    if (baselineEl) {
      baselineEl.textContent = d.baseline_kw
        ? `Baseline: ${d.baseline_kw.toFixed(3)} kW`
        : "Baseline: -- kW";
    }

    const lastUpdateEl = document.getElementById("last-update");
    if (lastUpdateEl) {
      lastUpdateEl.textContent = new Date().toLocaleTimeString();
    }
  } catch {
    updateConnectionStatus(false);
  }
}

async function updatePowerChart() {
  if (!powerChart) return;

  try {
    const res = await fetch(`/api/history?hours=${currentTimeRange}`);
    if (!res.ok) return;

    const data = await res.json();
    if (!data.data?.length) return;

    powerChart.data.datasets[0].data = data.data.map((p) => ({
      x: new Date(p.timestamp),
      y: p.power_kw,
    }));

    powerChart.update("none");
  } catch (e) {
    console.error("Chart update error:", e);
  }
}

async function updateStatistics() {
  try {
    const res = await fetch("/api/statistics");
    if (!res.ok) return;

    const s = await res.json();

    const avgEl = document.getElementById("avg-power");
    if (avgEl) avgEl.textContent = `${s.average_kw.toFixed(3)} kW`;

    const maxEl = document.getElementById("max-power");
    if (maxEl) maxEl.textContent = `${s.max_kw.toFixed(3)} kW`;

    const minEl = document.getElementById("min-power");
    if (minEl) minEl.textContent = `${s.min_kw.toFixed(3)} kW`;

    const alertCountEl = document.getElementById("alert-count");
    if (alertCountEl) alertCountEl.textContent = s.alerts ?? 0;

    const spikeEl = document.getElementById("spike-count");
    if (spikeEl) spikeEl.textContent = s.spikes ?? 0;
  } catch (e) {
    console.error("Statistics update error:", e);
  }
}

async function checkForNewAlerts(previousCount = 0) {
  try {
    const response = await fetch("/api/alerts?limit=1");
    if (!response.ok) return previousCount;

    const alerts = await response.json();

    if (alerts.length > 0 && alerts[0].id > previousCount) {
      const alert = alerts[0];

      if (notificationSettings && notificationSettings.enabled) {
        const deviation = Math.abs(alert.deviation_percent).toFixed(1);
        const powerStr = alert.power_kw.toFixed(2);
        const baselineStr = alert.baseline_kw ? alert.baseline_kw.toFixed(2) : "N/A";

        showAlertNotification(
          `⚡ Anomaly Detected!`,
          `Power: ${powerStr} kW (Baseline: ${baselineStr} kW)\nDeviation: ${deviation}%`
        );
      }

      return alert.id;
    }
  } catch (error) {
    console.log("Could not check for new alerts");
  }
  return previousCount;
}

async function updateAlerts() {
  try {
    const res = await fetch("/api/alerts?limit=10");
    if (!res.ok) return;

    const alerts = await res.json();
    const list = document.getElementById("alerts-list");
    const badge = document.getElementById("alert-count-badge");

    allAlerts = alerts;

    if (badge) {
      badge.textContent = alerts.length;
    }

    if (list) {
      if (alerts.length === 0) {
        list.innerHTML = `
          <div class="no-alerts">
            <p>✅ No alerts detected</p>
            <p class="subtext">System operating normally</p>
          </div>
        `;
      } else {
        list.innerHTML = alerts
          .map(
            (a) => `
          <div class="alert-item" style="cursor:pointer; border-left: 4px solid ${getSeverityColor(a.severity || "medium")};" onclick="openAlertModal(${a.id})">
            <div class="alert-header">
              <span class="alert-type">⚠️ ${a.alert_type || "Consumption Spike"}</span>
              <span class="alert-time">${new Date(a.timestamp).toLocaleString()}</span>
            </div>
            <div class="alert-details">
              Power: ${a.power_kw ? a.power_kw.toFixed(3) : "--"} kW | 
              Baseline: ${a.baseline_kw ? a.baseline_kw.toFixed(3) : "--"} kW | 
              Deviation: ${a.deviation_percent ? a.deviation_percent.toFixed(1) : "--"}%
            </div>
          </div>`,
          )
          .join("");
      }
    }

    const newId = await checkForNewAlerts(lastAlertId);
    if (newId) {
      lastAlertId = newId;
    }
  } catch (e) {
    console.error("Alerts update error:", e);
  }
}

function updateAll() {
  updateCurrentPower();
  updatePowerChart();
  updateStatistics();
  updateAlerts();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// MODAL FUNCTIONS - WITH ALERT FEEDBACK
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

let currentAlertId = null;

function getSeverityColor(severity) {
  const colors = {
    low: "#4CAF50",
    medium: "#ff9800",
    high: "#ff5252",
    critical: "#b71c1c",
  };
  return colors[severity] || "#999";
}

function getSeverityBadge(severity) {
  const badges = {
    low: "● Low",
    medium: "● Medium",
    high: "● High",
    critical: "● Critical",
  };
  return badges[severity] || severity;
}

function getDeviationColor(deviation) {
  const dev = Math.abs(deviation);
  if (dev > 50) return "#b71c1c";
  if (dev > 30) return "#ff5252";
  if (dev > 15) return "#ff9800";
  return "#4CAF50";
}

function openAlertModal(alertId) {
  console.log("Opening alert modal for ID:", alertId);
  const modal = document.getElementById("alert-modal");

  if (!alertId) {
    loadModalAlerts();
    if (modal) {
      modal.classList.add("show");
      modal.style.display = "flex";
    }
    return;
  }

  const alert = allAlerts.find((a) => a.id === alertId);
  if (!alert) {
    console.error("Alert not found:", alertId);
    return;
  }

  currentAlertId = alertId;

  const list = document.getElementById("modal-alert-list");
  list.innerHTML = `
        <div class="alert-detail-view">
            <h3>Alert #${alert.id}</h3>
            
            <div class="detail-section">
                <h4>Incident Details</h4>
                <div class="detail-row">
                    <span class="label">Time:</span>
                    <span class="value">${new Date(alert.timestamp).toLocaleString()}</span>
                </div>
                <div class="detail-row">
                    <span class="label">Power Consumption:</span>
                    <span class="value">${alert.power_kw.toFixed(3)} kW</span>
                </div>
                <div class="detail-row">
                    <span class="label">Baseline:</span>
                    <span class="value">${alert.baseline_kw.toFixed(3)} kW</span>
                </div>
                <div class="detail-row">
                    <span class="label">Deviation:</span>
                    <span class="value" style="color: ${getDeviationColor(alert.deviation_percent)}">
                        ${alert.deviation_percent.toFixed(2)}%
                    </span>
                </div>
            </div>
            
            ${
              alert.severity
                ? `
                <div class="detail-section">
                    <h4>Severity</h4>
                    <div class="severity-badge" style="background: ${getSeverityColor(alert.severity)}; color: white; padding: 0.5rem; border-radius: 4px; display: inline-block;">
                        ${getSeverityBadge(alert.severity)}
                    </div>
                </div>
            `
                : ""
            }
            
            ${
              alert.user_feedback
                ? `
                <div class="detail-section" style="background: #f0f0f0; padding: 1rem; border-radius: 8px;">
                    <h4>Your Feedback</h4>
                    <p><strong>${alert.user_feedback}</strong></p>
                    <small>Recorded: ${new Date(alert.feedback_at).toLocaleString()}</small>
                </div>
            `
                : ""
            }
            
            <div class="detail-section">
                <h4>What do you think?</h4>
                <p>Help us improve by providing feedback:</p>
                <div class="action-buttons" style="display: flex; gap: 1rem; flex-direction: column;">
                    <button class="btn-primary" onclick="markAlertFeedback(${alert.id}, 'true_positive')" style="background: #4CAF50;">
                        ✓ True Positive - Real Anomaly
                    </button>
                    <button class="btn-warning" onclick="markAlertFeedback(${alert.id}, 'false_positive')" style="background: #ff9800;">
                        ✗ False Positive - Not an Issue
                    </button>
                    <button class="btn-primary" onclick="acknowledgeAlert(${alert.id})">
                        👁️ Acknowledge & Dismiss
                    </button>
                </div>
            </div>
        </div>
    `;

  if (modal) {
    modal.classList.add("show");
    modal.style.display = "flex";
  }
}

function closeAlertModal() {
  console.log("Closing alert modal...");
  const modal = document.getElementById("alert-modal");
  if (modal) {
    modal.classList.remove("show");
    modal.style.display = "none";
  }
  currentAlertId = null;
}

async function markAlertFeedback(alertId, feedbackType) {
  try {
    const response = await fetch(`/api/alerts/${alertId}/feedback`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ feedback: feedbackType }),
    });

    if (!response.ok) throw new Error("Failed to save feedback");

    const alert = allAlerts.find((a) => a.id === alertId);
    if (alert) {
      alert.user_feedback = feedbackType;
      alert.feedback_at = new Date().toISOString();
    }

    const feedbackLabel = feedbackType === "true_positive" ? "True Positive" : "False Positive";
    if (typeof showNotification === "function") {
      showNotification(`✓ Feedback recorded: ${feedbackLabel}`, "success");
    }

    closeAlertModal();
    updateAlerts();
  } catch (error) {
    console.error("Error saving feedback:", error);
    if (typeof showNotification === "function") {
      showNotification("Failed to save feedback", "error");
    }
  }
}

async function acknowledgeAlert(alertId) {
  try {
    const response = await fetch(`/api/alerts/${alertId}/acknowledge`, {
      method: "POST",
    });

    if (!response.ok) throw new Error("Failed to acknowledge");

    const alert = allAlerts.find((a) => a.id === alertId);
    if (alert) alert.status = "acknowledged";

    if (typeof showNotification === "function") {
      showNotification("Alert acknowledged", "success");
    }

    closeAlertModal();
    loadModalAlerts();
    updateAlerts();
  } catch (error) {
    console.error("Error acknowledging alert:", error);
    if (typeof showNotification === "function") {
      showNotification("Failed to acknowledge alert", "error");
    }
  }
}

async function loadModalAlerts(filter = "all") {
  const list = document.getElementById("modal-alert-list");
  if (!list) {
    console.error("Modal alert list element not found!");
    return;
  }

  list.innerHTML = '<div class="loading">⏳ Loading alerts...</div>';

  try {
    const res = await fetch("/api/alerts?limit=500");
    if (!res.ok) {
      throw new Error("Failed to fetch alerts");
    }

    allAlerts = await res.json();

    console.log(`Loaded ${allAlerts.length} alerts`);

    if (allAlerts.length === 0) {
      list.innerHTML = `
                <div class="no-alerts-modal">
                    <p>✅ No alerts found</p>
                    <p class="subtext">System has been operating normally</p>
                </div>
            `;
    } else {
      list.innerHTML = allAlerts
        .map(
          (a) => `
                <div class="modal-alert-item" 
                     style="border-left: 4px solid ${getSeverityColor(a.severity || "medium")}; cursor: pointer;"
                     onclick="openAlertModal(${a.id})">
                    <div class="modal-alert-header">
                        <span class="modal-alert-type">
                            ${a.severity ? `<span style="color: ${getSeverityColor(a.severity)}">${getSeverityBadge(a.severity)}</span> ` : ""}
                            ⚠️ ${a.alert_type || "Consumption Spike"}
                        </span>
                        <span class="modal-alert-time">${new Date(a.timestamp).toLocaleString()}</span>
                    </div>
                    <div class="modal-alert-details">
                        <strong>Power:</strong> ${a.power_kw ? a.power_kw.toFixed(3) : "--"} kW | 
                        <strong>Baseline:</strong> ${a.baseline_kw ? a.baseline_kw.toFixed(3) : "--"} kW | 
                        <strong>Deviation:</strong> ${a.deviation_percent ? a.deviation_percent.toFixed(1) : "--"}%
                        ${a.user_feedback ? `<br><strong>Feedback:</strong> ${a.user_feedback}` : ""}
                    </div>
                </div>`,
        )
        .join("");
    }
  } catch (error) {
    console.error("Error loading alerts:", error);
    list.innerHTML = `
            <div class="no-alerts-modal">
                <p>❌ Error loading alerts</p>
                <p class="subtext">${error.message}</p>
            </div>
        `;
  }
}

async function filterAlerts() {
  const severity = document.getElementById("severity-filter")?.value;
  const status = document.getElementById("status-filter")?.value;

  let filtered = allAlerts;

  if (severity) {
    filtered = filtered.filter((a) => a.severity === severity);
  }
  if (status) {
    filtered = filtered.filter((a) => a.status === status);
  }

  const list = document.getElementById("modal-alert-list");

  if (filtered.length === 0) {
    list.innerHTML =
      '<div class="no-alerts-modal"><p>No alerts match filters</p></div>';
    return;
  }

  list.innerHTML = filtered
    .map(
      (a) => `
        <div class="modal-alert-item" 
             style="border-left: 4px solid ${getSeverityColor(a.severity || "medium")}; cursor: pointer;"
             onclick="openAlertModal(${a.id})">
            <div class="modal-alert-header">
                <span class="modal-alert-type">
                    ${a.severity ? `<span style="color: ${getSeverityColor(a.severity)}">${getSeverityBadge(a.severity)}</span> ` : ""}
                    ⚠️ ${a.alert_type || "Consumption Spike"}
                </span>
                <span class="modal-alert-time">${new Date(a.timestamp).toLocaleString()}</span>
            </div>
            <div class="modal-alert-details">
                <strong>Power:</strong> ${a.power_kw ? a.power_kw.toFixed(3) : "--"} kW | 
                <strong>Baseline:</strong> ${a.baseline_kw ? a.baseline_kw.toFixed(3) : "--"} kW | 
                <strong>Deviation:</strong> ${a.deviation_percent ? a.deviation_percent.toFixed(1) : "--"}%
                ${a.user_feedback ? `<br><strong>Feedback:</strong> ${a.user_feedback}` : ""}
            </div>
        </div>`,
    )
    .join("");
}

async function clearAllAlerts() {
  if (typeof showConfirmNotification !== "function") return;

  showConfirmNotification(
    "Clear all alerts? This cannot be undone.",
    async () => {
      try {
        if (typeof showNotification === "function") {
          showNotification("🗑️ Clearing alerts...", "info");
        }

        const res = await fetch("/api/alerts", { method: "DELETE" });
        if (!res.ok) {
          throw new Error("Failed to clear alerts");
        }

        const result = await res.json();

        if (typeof showNotification === "function") {
          showNotification(`Successfully cleared ${result.cleared_count} alerts`, "success");
        }

        loadModalAlerts();
        updateAlerts();
      } catch (error) {
        console.error("Error clearing alerts:", error);
        if (typeof showNotification === "function") {
          showNotification("Failed to clear alerts", "error");
        }
      }
    },
    () => {
      if (typeof showNotification === "function") {
        showNotification("Clear alerts canceled", "warning");
      }
    }
  );
}

function exportAlertsToCSV() {
  if (allAlerts.length === 0) {
    if (typeof showNotification === "function") {
      showNotification("No alerts to export", "warning");
    }
    return;
  }

  let csv = "ID,Timestamp,Power (kW),Baseline (kW),Deviation (%),Severity,Status,Created At\n";
  
  for (const alert of allAlerts) {
    csv += `${alert.id},"${alert.timestamp}",${alert.power_kw},${alert.baseline_kw},${alert.deviation_percent.toFixed(2)},"${alert.severity || 'N/A'}","${alert.status || 'N/A'}","${alert.created_at}"\n`;
  }

  const blob = new Blob([csv], { type: "text/csv" });
  const url = window.URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = `alerts_${new Date().toISOString().split('T')[0]}.csv`;
  document.body.appendChild(a);
  a.click();
  window.URL.revokeObjectURL(url);
  document.body.removeChild(a);
  
  if (typeof showNotification === "function") {
    showNotification("Alerts exported to CSV", "success");
  }
  console.log("✓ Alerts exported to CSV");
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INITIALIZATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

document.addEventListener("DOMContentLoaded", () => {
  console.log("📊 Dashboard initializing...");

  initPowerChart();
  updateAll();
  updateInterval = setInterval(updateAll, 30000);

  const timeRangeSelect = document.getElementById("time-range");
  if (timeRangeSelect) {
    timeRangeSelect.addEventListener("change", (e) => {
      currentTimeRange = Number(e.target.value);
      updatePowerChart();
    });
  }

  const alertsStat = document.getElementById("alerts-stat-trigger");
  if (alertsStat) {
    alertsStat.addEventListener("click", () => {
      openAlertModal();
    });
    alertsStat.style.cursor = "pointer";
  }

  const alertsCard = document.querySelector(".alerts-card .card-header");
  if (alertsCard) {
    alertsCard.addEventListener("click", () => {
      openAlertModal();
    });
    alertsCard.style.cursor = "pointer";
  }

  const recentAlertsHeader = document.getElementById("alerts-header-trigger");
  if (recentAlertsHeader) {
    recentAlertsHeader.addEventListener("click", () => {
      openAlertModal();
    });
    recentAlertsHeader.style.cursor = "pointer";
  }

  const alertBadge = document.getElementById("alert-count-badge");
  if (alertBadge) {
    alertBadge.addEventListener("click", (e) => {
      e.stopPropagation();
      openAlertModal();
    });
    alertBadge.style.cursor = "pointer";
  }

  const closeModalBtn = document.getElementById("close-modal");
  if (closeModalBtn) {
    closeModalBtn.addEventListener("click", closeAlertModal);
  }

  const closeModalFooterBtn = document.getElementById("close-modal-btn");
  if (closeModalFooterBtn) {
    closeModalFooterBtn.addEventListener("click", closeAlertModal);
  }

  const modal = document.getElementById("alert-modal");
  if (modal) {
    modal.addEventListener("click", (e) => {
      if (e.target === modal) {
        closeAlertModal();
      }
    });
  }

  const clearAlertsBtn = document.getElementById("clear-alerts-btn");
  if (clearAlertsBtn) {
    clearAlertsBtn.addEventListener("click", clearAllAlerts);
  }

  const exportAlertsBtn = document.getElementById("export-alerts-btn");
  if (exportAlertsBtn) {
    exportAlertsBtn.addEventListener("click", exportAlertsToCSV);
  }

  const severityFilter = document.getElementById("severity-filter");
  if (severityFilter) {
    severityFilter.addEventListener("change", filterAlerts);
  }

  const statusFilter = document.getElementById("status-filter");
  if (statusFilter) {
    statusFilter.addEventListener("change", filterAlerts);
  }

  console.log("✅ Dashboard initialized successfully!");
});

window.addEventListener("beforeunload", () => {
  if (updateInterval) {
    clearInterval(updateInterval);
  }
});
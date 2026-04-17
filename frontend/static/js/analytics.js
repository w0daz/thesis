/**
 * Analytics Page - Pattern Analysis & Comparisons
 * With PDF Export Functionality
 */

let comparisonChart = null;
let weekdayChart = null;
let heatmapChart = null;
let baselineChart = null;

// Store analytics data for PDF export
let analyticsData = {
    hourlyPattern: null,
    dailyConsumption: null,
    weekdayStats: null,
    baselineData: null,
    comparisonData: null,
    statistics: null
};

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// UTILITY FUNCTIONS
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function updateConnectionStatus(connected) {
  const statusBadge = document.getElementById("connection-status");
  if (!statusBadge) return;

  const statusDot = statusBadge.querySelector(".status-dot");
  const statusText = statusBadge.querySelector(".status-text");

  if (connected) {
    statusDot.classList.remove("disconnected");
    statusText.textContent = "Connected";
  } else {
    statusDot.classList.add("disconnected");
    statusText.textContent = "Disconnected";
  }
}

function notify(message, type = "info") {
  if (typeof showNotification === "function") {
    showNotification(message, type);
  }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// CHART INITIALIZATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

function initComparisonChart() {
  const ctx = document.getElementById("comparisonChart").getContext("2d");

  comparisonChart = new Chart(ctx, {
    type: "line",
    data: {
      datasets: [
        {
          label: "Current Consumption",
          data: [],
          borderColor: "#667eea",
          backgroundColor: "rgba(102, 126, 234, 0.1)",
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 0,
        },
        {
          label: "Baseline Average",
          data: [],
          borderColor: "#4CAF50",
          backgroundColor: "rgba(76, 175, 80, 0.1)",
          borderWidth: 2,
          borderDash: [5, 5],
          fill: false,
          tension: 0.4,
          pointRadius: 0,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      interaction: {
        intersect: false,
        mode: "index",
      },
      plugins: {
        legend: {
          display: true,
          position: "top",
        },
      },
      scales: {
        x: {
          type: "time",
          time: {
            unit: "hour",
            displayFormats: {
              hour: "HH:mm",
            },
          },
          title: {
            display: true,
            text: "Time",
          },
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Power (kW)",
          },
        },
      },
    },
  });
}

function initBaselineChart() {
  const ctx = document.getElementById("baselineChart").getContext("2d");

  baselineChart = new Chart(ctx, {
    type: "line",
    data: {
      labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      datasets: [
        {
          label: "Average Consumption",
          data: [],
          borderColor: "#4CAF50",
          backgroundColor: "rgba(76, 175, 80, 0.1)",
          borderWidth: 3,
          fill: true,
          tension: 0.4,
          pointRadius: 4,
          pointBackgroundColor: "#4CAF50",
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      scales: {
        x: {
          title: {
            display: true,
            text: "Hour of Day",
          },
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Power (kW)",
          },
        },
      },
    },
  });
}

function initWeekdayChart() {
  const ctx = document.getElementById("weekdayChart").getContext("2d");

  weekdayChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: ["Weekday", "Weekend"],
      datasets: [
        {
          label: "Average Consumption",
          data: [0, 0],
          backgroundColor: [
            "rgba(102, 126, 234, 0.8)",
            "rgba(255, 99, 132, 0.8)",
          ],
          borderColor: ["#667eea", "#ff6384"],
          borderWidth: 2,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Average Power (kW)",
          },
        },
      },
    },
  });
}

function initHeatmapChart() {
  const ctx = document.getElementById("heatmapChart").getContext("2d");

  heatmapChart = new Chart(ctx, {
    type: "bar",
    data: {
      labels: Array.from({ length: 24 }, (_, i) => `${i}:00`),
      datasets: [
        {
          label: "Average Consumption by Hour",
          data: Array(24).fill(0),
          backgroundColor: "rgba(102, 126, 234, 0.6)",
          borderColor: "#667eea",
          borderWidth: 1,
        },
      ],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      plugins: {
        legend: {
          display: false,
        },
      },
      scales: {
        x: {
          title: {
            display: true,
            text: "Hour of Day",
          },
        },
        y: {
          beginAtZero: true,
          title: {
            display: true,
            text: "Power (kW)",
          },
        },
      },
    },
  });
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// DATA UPDATES
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function updateComparisonChart() {
  try {
    const hours = parseInt(document.getElementById("comparison-range").value);

    const historyResponse = await fetch(`/api/history?hours=${hours}`);
    if (!historyResponse.ok) return;

    const historyData = await historyResponse.json();

    const baselineResponse = await fetch("/api/baseline");
    if (!baselineResponse.ok) return;

    const baselineData = await baselineResponse.json();

    if (!historyData.data || !baselineData.hourly_baseline) {
      console.warn("Missing data for comparison chart");
      notify("Missing data for comparison chart", "warning");
      return;
    }

    const currentData = historyData.data.map((item) => ({
      x: new Date(item.timestamp),
      y: item.power_kw,
    }));

    const baselineOverlay = historyData.data.map((item) => {
      const hour = new Date(item.timestamp).getHours();
      const hourBaseline = baselineData.hourly_baseline[hour.toString()];
      return {
        x: new Date(item.timestamp),
        y: hourBaseline ? hourBaseline.mean : null,
      };
    });

    comparisonChart.data.datasets[0].data = currentData;
    comparisonChart.data.datasets[1].data = baselineOverlay;
    comparisonChart.update("none");

    // Store for PDF export
    analyticsData.comparisonData = { currentData, baselineOverlay, hours };

    updateConnectionStatus(true);
  } catch (error) {
    console.error("Error updating comparison chart:", error);
    updateConnectionStatus(false);
    notify("Error updating comparison chart", "error");
  }
}

async function updateBaseline(recalculate = false) {
  try {
    const url = recalculate
      ? "/api/baseline?recalculate=true"
      : "/api/baseline";
    
    console.log("📊 Fetching baseline from:", url);
    
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000); // 10 second timeout
    
    const response = await fetch(url, { signal: controller.signal });
    clearTimeout(timeoutId);

    console.log("📊 Baseline response status:", response.status);

    if (!response.ok) {
      console.error("❌ Baseline API Error:", response.status, response.statusText);
      notify("Failed to load baseline data", "error");
      return;
    }

    const data = await response.json();
    console.log("📊 Baseline data received:", data);

    if (!data.hourly_baseline) {
      console.error("❌ No hourly_baseline in response");
      console.log("📊 Full response:", data);
      notify("Baseline data missing in response", "warning");
      return;
    }

    // Build array with 24 hours (fill missing with 0)
    const baselineData = [];
    for (let hour = 0; hour < 24; hour++) {
      const hourStr = hour.toString();
      const hourData = data.hourly_baseline[hourStr];
      baselineData.push(hourData ? hourData.mean : 0); // Use 0 instead of null
    }

    console.log("📊 Baseline data extracted:", baselineData);
    console.log("📊 Chart instance exists:", !!baselineChart);
    
    if (!baselineChart) {
      console.error("❌ Baseline chart not initialized");
      notify("Baseline chart not initialized", "error");
      return;
    }
    
    baselineChart.data.datasets[0].data = baselineData;
    baselineChart.update();

    // Store for PDF export
    analyticsData.baselineData = data.hourly_baseline;
    
    console.log("✅ Baseline chart updated successfully");
    if (recalculate) {
      notify("Baseline recalculated successfully", "success");
    }
  } catch (error) {
    console.error("❌ Error updating baseline:", error);
    if (error.name === "AbortError") {
      console.error("❌ Baseline request timed out after 10 seconds");
      notify("Baseline request timed out", "error");
    } else {
      notify("Failed to update baseline", "error");
    }
  }
}

async function updateAnalytics() {
    try {
        const response = await fetch('/api/analytics');

        if (!response.ok) {
            console.warn('Analytics API Error:', response.status);
            notify("Failed to load analytics data", "error");
            return;
        }

        const data = await response.json();
        
        console.log('📊 Analytics data received:', data);

        /* ───────── Hourly Heatmap ───────── */
        if (data.hourly_pattern) {
            const hourlyData = [];
            for (let hour = 0; hour < 24; hour++) {
                const hourStr = hour.toString();
                const hourData = data.hourly_pattern[hourStr];
                
                if (hourData && hourData.mean !== undefined) {
                    hourlyData.push(hourData.mean);
                } else {
                    hourlyData.push(0);
                }
            }

            console.log('📈 Hourly data:', hourlyData);

            const maxValue = Math.max(...hourlyData);
            const colors = hourlyData.map(value => {
                if (!maxValue || !value) return 'rgba(102, 126, 234, 0.3)';
                const intensity = value / maxValue;
                return `rgba(102, 126, 234, ${0.3 + intensity * 0.7})`;
            });

            heatmapChart.data.datasets[0].data = hourlyData;
            heatmapChart.data.datasets[0].backgroundColor = colors;
            heatmapChart.update();
            
            console.log('✅ Heatmap updated');
            
            // Store for PDF export
            analyticsData.hourlyPattern = data.hourly_pattern;
        }

        /* ───────── Weekday vs Weekend ───────── */
        if (data.daily_consumption) {
            let weekdayTotal = 0;
            let weekdayCount = 0;
            let weekendTotal = 0;
            let weekendCount = 0;

            data.daily_consumption.forEach(item => {
                const date = new Date(item.date);
                const day = date.getDay();

                if (day === 0 || day === 6) {
                    weekendTotal += item.average_kw;
                    weekendCount++;
                } else {
                    weekdayTotal += item.average_kw;
                    weekdayCount++;
                }
            });

            const weekdayAvg = weekdayCount ? weekdayTotal / weekdayCount : 0;
            const weekendAvg = weekendCount ? weekendTotal / weekendCount : 0;

            console.log('📅 Weekday avg:', weekdayAvg, 'Weekend avg:', weekendAvg);

            weekdayChart.data.datasets[0].data = [
                weekdayAvg,
                weekendAvg
            ];

            weekdayChart.update();
            
            console.log('✅ Weekday chart updated');
            
            // Store for PDF export
            analyticsData.dailyConsumption = data.daily_consumption;
            analyticsData.weekdayStats = {
                weekday: weekdayAvg,
                weekend: weekendAvg,
                difference: Math.abs(weekdayAvg - weekendAvg),
                percentDiff: weekdayAvg ? ((weekendAvg - weekdayAvg) / weekdayAvg * 100) : 0
            };
        }

    } catch (error) {
        console.error('Error updating analytics:', error);
        notify("Error updating analytics charts", "error");
    }
}

async function fetchStatistics() {
    try {
        const response = await fetch('/api/statistics');
        if (!response.ok) {
            notify("Failed to load statistics", "warning");
            return;
        }
        
        analyticsData.statistics = await response.json();
    } catch (error) {
        console.error('Error fetching statistics:', error);
        notify("Error fetching statistics", "error");
    }
}

function updateAll() {
  console.log("🔄 Refreshing analytics...");
  updateComparisonChart();
  updateBaseline();
  updateAnalytics();
  fetchStatistics();
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// PDF EXPORT FUNCTIONALITY
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async function exportToPDF() {
    const btn = document.getElementById('export-pdf-btn');
    const originalText = btn.querySelector('.text').textContent;
    
    try {
        // Show loading state
        btn.classList.add('loading');
        btn.disabled = true;
        btn.querySelector('.text').textContent = 'Generating PDF...';
        
        console.log('📄 Starting PDF export...');
        notify("Generating PDF report...", "info");
        
        // Prepare comprehensive analytics data
        const pdfData = {
            generatedAt: new Date().toISOString(),
            statistics: analyticsData.statistics,
            hourlyPattern: analyticsData.hourlyPattern,
            weekdayStats: analyticsData.weekdayStats,
            baselineData: analyticsData.baselineData,
            dailyConsumption: analyticsData.dailyConsumption
        };
        
        console.log('📦 PDF data prepared:', pdfData);
        
        // Send to backend for PDF generation
        const response = await fetch('/api/export/pdf', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(pdfData)
        });
        
        if (!response.ok) {
            throw new Error(`PDF generation failed: ${response.status}`);
        }
        
        // Get the PDF blob
        const blob = await response.blob();
        
        // Create download link
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `energy-analytics-report-${new Date().toISOString().split('T')[0]}.pdf`;
        document.body.appendChild(a);
        a.click();
        
        // Cleanup
        window.URL.revokeObjectURL(url);
        document.body.removeChild(a);
        
        console.log('✅ PDF exported successfully!');
        notify("PDF downloaded successfully", "success");
        
        // Success feedback
        btn.querySelector('.text').textContent = 'Downloaded!';
        setTimeout(() => {
            btn.querySelector('.text').textContent = originalText;
        }, 2000);
        
    } catch (error) {
        console.error('❌ Error exporting PDF:', error);
        notify("Failed to generate PDF. Please try again.", "error");
        btn.querySelector('.text').textContent = 'Export Failed';
        setTimeout(() => {
            btn.querySelector('.text').textContent = originalText;
        }, 2000);
    } finally {
        btn.classList.remove('loading');
        btn.disabled = false;
    }
}

// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
// INITIALIZATION
// ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

document.addEventListener("DOMContentLoaded", () => {
  console.log("📈 Analytics page initializing...");

  initComparisonChart();
  initBaselineChart();
  initWeekdayChart();
  initHeatmapChart();

  updateAll();

  // Event listeners
  document
    .getElementById("comparison-range")
    ?.addEventListener("change", updateComparisonChart);
    
  document.getElementById("refresh-baseline")?.addEventListener("click", () => {
    console.log("🔄 Recalculating baseline...");
    updateBaseline(true);
  });
  
  // PDF Export button
  document.getElementById("export-pdf-btn")?.addEventListener("click", exportToPDF);

  console.log("✅ Analytics initialized!");
});
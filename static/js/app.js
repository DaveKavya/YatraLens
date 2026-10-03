/* ─────────────────────────────────────────────────────────────
   YatraLens – app.js
   Handles: filter submission, chart rendering via Plotly,
            table sorting, upload drag-and-drop, print report.
   ───────────────────────────────────────────────────────────── */

"use strict";

// ── Plotly chart renderer ──────────────────────────────────────
/**
 * Render a Plotly chart from server-provided JSON string.
 * @param {string} containerId – DOM element ID
 * @param {string} jsonStr     – JSON serialised Plotly figure
 */
function renderChart(containerId, jsonStr) {
  const el = document.getElementById(containerId);
  if (!el) return;
  try {
    const fig = JSON.parse(jsonStr);
    const layout = Object.assign({}, fig.layout, {
      autosize: true,
      responsive: true,
    });
    Plotly.newPlot(el, fig.data, layout, {
      displayModeBar: false,
      responsive: true,
      staticPlot: false,
    });
  } catch (e) {
    el.innerHTML = `<p style="color:#6b7280;padding:32px;text-align:center;">Chart unavailable.</p>`;
    console.error("Chart render error:", e);
  }
}

// ── Filter form: auto-submit on select change ─────────────────
document.addEventListener("DOMContentLoaded", function () {
  // Auto-submit filter form when any select changes
  const filterForm = document.getElementById("filter-form");
  if (filterForm) {
    filterForm.querySelectorAll("select").forEach(function (sel) {
      sel.addEventListener("change", function () {
        filterForm.submit();
      });
    });
  }

  // ── Table sorting ────────────────────────────────────────────
  document.querySelectorAll("table.data-table.sortable").forEach(function (table) {
    const headers = table.querySelectorAll("thead th[data-sort]");
    let currentCol = null;
    let ascending = true;

    headers.forEach(function (th) {
      th.style.cursor = "pointer";
      th.addEventListener("click", function () {
        const col = th.dataset.sort;
        const isNum = th.dataset.type === "num";

        if (currentCol === col) {
          ascending = !ascending;
        } else {
          ascending = true;
          if (currentCol) {
            const prevTh = table.querySelector(`th[data-sort="${currentCol}"]`);
            if (prevTh) {
              prevTh.classList.remove("sorted");
              prevTh.querySelector(".sort-arrow").textContent = "↕";
            }
          }
          currentCol = col;
        }

        th.classList.add("sorted");
        th.querySelector(".sort-arrow").textContent = ascending ? "↑" : "↓";

        const tbody = table.querySelector("tbody");
        const rows = Array.from(tbody.querySelectorAll("tr"));

        rows.sort(function (a, b) {
          const aCell = a.querySelector(`td[data-col="${col}"]`);
          const bCell = b.querySelector(`td[data-col="${col}"]`);
          if (!aCell || !bCell) return 0;
          let aVal = aCell.dataset.val || aCell.textContent.trim();
          let bVal = bCell.dataset.val || bCell.textContent.trim();

          if (isNum) {
            aVal = parseFloat(aVal) || 0;
            bVal = parseFloat(bVal) || 0;
            return ascending ? aVal - bVal : bVal - aVal;
          } else {
            return ascending
              ? aVal.localeCompare(bVal)
              : bVal.localeCompare(aVal);
          }
        });

        rows.forEach(function (row) { tbody.appendChild(row); });
      });
    });
  });

  // ── Upload drag-and-drop ─────────────────────────────────────
  const dropzone = document.getElementById("upload-dropzone");
  const fileInput = document.getElementById("csv-file-input");
  const fileLabel = document.getElementById("file-label");

  if (dropzone && fileInput) {
    // Click on dropzone opens file picker
    dropzone.addEventListener("click", function () {
      fileInput.click();
    });

    fileInput.addEventListener("change", function () {
      updateFileLabel(fileInput.files[0]);
    });

    dropzone.addEventListener("dragover", function (e) {
      e.preventDefault();
      dropzone.classList.add("drag-over");
    });

    dropzone.addEventListener("dragleave", function () {
      dropzone.classList.remove("drag-over");
    });

    dropzone.addEventListener("drop", function (e) {
      e.preventDefault();
      dropzone.classList.remove("drag-over");
      const files = e.dataTransfer.files;
      if (files.length > 0) {
        fileInput.files = files;
        updateFileLabel(files[0]);
      }
    });

    function updateFileLabel(file) {
      if (file && fileLabel) {
        fileLabel.textContent = `Selected: ${file.name} (${formatBytes(file.size)})`;
        fileLabel.style.color = "var(--secondary)";
      }
    }
  }

  // ── Print report ─────────────────────────────────────────────
  const printBtn = document.getElementById("btn-print-report");
  if (printBtn) {
    printBtn.addEventListener("click", function () {
      window.print();
    });
  }

  // ── Number counter animation on dashboard ───────────────────
  document.querySelectorAll(".kpi-value[data-count]").forEach(function (el) {
    const target = parseInt(el.dataset.count, 10);
    if (isNaN(target)) return;
    const duration = 800;
    const step = Math.ceil(target / (duration / 16));
    let current = 0;
    const timer = setInterval(function () {
      current = Math.min(current + step, target);
      el.textContent = formatNumber(current);
      if (current >= target) clearInterval(timer);
    }, 16);
  });
});

// ── Utility: format bytes ─────────────────────────────────────
function formatBytes(bytes) {
  if (bytes < 1024) return bytes + " B";
  if (bytes < 1048576) return (bytes / 1024).toFixed(1) + " KB";
  return (bytes / 1048576).toFixed(1) + " MB";
}

// ── Utility: format numbers with commas ──────────────────────
function formatNumber(n) {
  return n.toLocaleString("en-IN");
}

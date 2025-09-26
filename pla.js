(function () {
  // -------- CONFIG --------
  const DISPLAY_TICKER = "ICICIBANK";       // Company name to display in tooltip
  const DATA_URL = "../pla.json";           // Path to your JSON feed
  const POLL_INTERVAL_MS = 5000;            // Poll every 5s
  const MAX_POINTS = 200;                   // Show max 200 points
  const CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js";
  const CANVAS_ID = "mainChart";
  const DEBUG_ID = "chartDebugOverlay";
  const SHOW_WARNINGS = false;
  // ------------------------

  const RANGE_OPTIONS = {
    "1H": 60 * 60 * 1000,
    "6H": 6 * 60 * 60 * 1000,
    "12H": 12 * 60 * 60 * 1000,
    "1D": 24 * 60 * 60 * 1000,
    "5D": 5 * 24 * 60 * 60 * 1000,
    "10D": 10 * 24 * 60 * 60 * 1000,
    "ALL": Infinity
  };

  let selectedRangeKey = "6H";
  let lastSelectedRangeKey = null;
  let lastPlottedTs = null;
  let lastPlottedPrice = null;
  let observedLatestTs = null;

  // Debug UI
  function ensureDebugBox() {
    let box = document.getElementById(DEBUG_ID);
    if (!box) {
      box = document.createElement("div");
      box.id = DEBUG_ID;
      box.style.position = "fixed";
      box.style.bottom = "12px";
      box.style.right = "12px";
      box.style.background = "rgba(0,0,0,0.7)";
      box.style.color = "#fff";
      box.style.padding = "8px 10px";
      box.style.borderRadius = "6px";
      box.style.fontFamily = "Orbitron, sans-serif";
      box.style.zIndex = 999999;
      box.style.fontSize = "11px";
      box.style.maxWidth = "340px";
      box.style.boxShadow = "0 6px 18px rgba(0,0,0,0.25)";
      box.style.display = "none";
      document.body.appendChild(box);
    }
    return box;
  }

  function showDebug(msg, isError = false) {
    if (!isError && !SHOW_WARNINGS) return;
    const box = ensureDebugBox();
    const time = new Date().toLocaleTimeString();
    box.innerHTML = `<strong>${isError ? "ERROR" : "STATUS"}</strong> [${time}] — ${msg}`;
    box.style.background = isError ? "rgba(160,10,10,0.9)" : "rgba(0,0,0,0.7)";
    box.style.display = "block";
    setTimeout(() => { box.style.display = "none"; }, isError ? 8000 : 4000);
    if (isError) console.error(msg); else console.log(msg);
  }

  // Script loader
  function loadScript(src) {
    return new Promise((resolve, reject) => {
      if (window.Chart) return resolve();
      const s = document.createElement("script");
      s.src = src;
      s.async = true;
      s.onload = resolve;
      s.onerror = () => reject(new Error("Failed to load " + src));
      document.head.appendChild(s);
    });
  }

  // Container + canvas
  function ensureContainerAndCanvas() {
    let container = document.querySelector(".header_box_two") || document.body;
    let canvas = document.getElementById(CANVAS_ID);
    if (!canvas) {
      const wrapper = document.createElement("div");
      wrapper.className = "chart-card";
      wrapper.style.width = "100%";
      wrapper.style.minHeight = "410px";
      wrapper.style.height = "420px";
      canvas = document.createElement("canvas");
      canvas.id = CANVAS_ID;
      canvas.style.width = "100%";
      canvas.style.height = "360px";
      wrapper.appendChild(canvas);
      container.appendChild(wrapper);
    }
    return canvas;
  }

  function parseRowTsMs(row) {
    const d = new Date(row.timestamp);
    return isNaN(d.getTime()) ? null : d.getTime();
  }

  // Chart creation
  function createChartOnCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    const cfg = {
      type: "line",
      data: {
        labels: [],
        datasets: [{
          data: [],
          borderColor: "#0668f1ff",
          backgroundColor: "#0668f12e",
          borderWidth: 2,
          pointRadius: 2,
          pointHoverRadius: 3,
          pointBackgroundColor: "#fff",
          pointBorderColor: "#006affff",
          pointBorderWidth: 2,
          tension: 0.1,
          fill: true
        }]
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        animation: false,
        plugins: {
          legend: { display: false },
          tooltip: {
            enabled: true,
            callbacks: {
              title: function (items) {
                if (!items.length) return "";
                const idx = items[0].dataIndex;
                const ts = items[0].chart._timestamps ? items[0].chart._timestamps[idx] : null;
                return ts ? new Date(Number(ts)).toLocaleString() : "";
              },
              label: function (context) {
                const price = context.formattedValue || context.raw;
                return `${DISPLAY_TICKER} — ${price}`;
              }
            }
          }
        },
        scales: {
          x: { display: false },
          y: {
            ticks: { color: "#aaa" },
            grid: { color: "rgba(255,255,255,0.08)" }
          }
        }
      }
    };
    const chart = new Chart(ctx, cfg);
    chart._timestamps = [];
    return chart;
  }

  // Range controls
  function ensureRangeControls(container) {
    const parent = container.querySelector(".chart-card") || container;
    let controls = parent.querySelector(".chart-range-controls");
    if (!controls) {
      controls = document.createElement("div");
      controls.className = "chart-range-controls";
      controls.style.display = "flex";
      controls.style.gap = "6px";
      controls.style.marginBottom = "8px";
      parent.insertBefore(controls, parent.firstChild);
    }

    controls.innerHTML = Object.keys(RANGE_OPTIONS).map(k => {
      const isActive = k === selectedRangeKey;
      return `<button data-range="${k}" style="
        padding:6px 10px;
        border-radius:6px;
        border:1px solid #ccc;
        cursor:pointer;
        font-family: Orbitron, sans-serif;
        background:${isActive ? "#f59b0b" : "#fff"};
        color:${isActive ? "#fff" : "#000"}">${k}</button>`;
    }).join("");

    if (!controls._hasHandler) {
      controls.addEventListener("click", ev => {
        const b = ev.target.closest("button[data-range]");
        if (b) setSelectedRange(b.getAttribute("data-range"));
      });
      controls._hasHandler = true;
    }
  }

  function setSelectedRange(key) {
    if (!Object.prototype.hasOwnProperty.call(RANGE_OPTIONS, key)) return;
    lastSelectedRangeKey = selectedRangeKey;
    selectedRangeKey = key;
    if (window._chartInstance) {
      updateChartFromJson(window._chartInstance, { forceFull: true });
    }
  }

  // Helpers
  const EPS = 1e-9;
  const nearlyEqual = (a, b) => Math.abs(a - b) <= EPS;

  function safeChartUpdate(chart) {
    if (!chart) return;
    if (chart.__updating) return;
    chart.__updating = true;
    requestAnimationFrame(() => {
      try { chart.update("none"); } catch { chart.update(); }
      chart.__updating = false;
    });
  }

  async function fetchJsonData(url, signal) {
    const r = await fetch(url, { cache: "no-store", signal });
    if (!r.ok) throw new Error(r.status + " " + r.statusText);
    return r.json();
  }

  // Chart updating
  let isUpdating = false, currentAbort = null, pollIntervalId = null;
  async function updateChartFromJson(chart, opts = { forceFull: false }) {
    if (isUpdating) return;
    isUpdating = true;
    try {
      if (currentAbort) currentAbort.abort();
      currentAbort = new AbortController();
      const json = await fetchJsonData(DATA_URL, currentAbort.signal);
      const matches = json.filter(e => e.ticker === DISPLAY_TICKER);
      if (!matches.length) {
        showDebug(`No entries for ticker "${DISPLAY_TICKER}" in JSON.`, true);
        return;
      }

      const normalized = matches.map(r => ({ row: r, tsMs: parseRowTsMs(r) }));
      const latestTs = Math.max(...normalized.map(n => n.tsMs || 0));
      if (!observedLatestTs || latestTs >= observedLatestTs) observedLatestTs = latestTs;

      // filter by range
      const datasetLatestTs = Math.max(...normalized.map(n => n.tsMs || 0));
      let filtered = normalized;
      if (datasetLatestTs && RANGE_OPTIONS[selectedRangeKey] !== Infinity) {
        const cutoff = datasetLatestTs - RANGE_OPTIONS[selectedRangeKey];
        filtered = normalized.filter(n => n.tsMs && n.tsMs >= cutoff);
        showDebug(`Range=${selectedRangeKey}, cutoff=${new Date(cutoff).toLocaleString()}, points=${filtered.length}`);
      }

      // build arrays
      const labels = [], prices = [];
      filtered.sort((a, b) => a.tsMs - b.tsMs).forEach(item => {
        const p = parseFloat(item.row.price);
        if (isFinite(p)) { labels.push(item.tsMs); prices.push(p); }
      });

      if (!prices.length) {
        showDebug("No valid price data to plot.", true);
        return;
      }

      // dedup consecutive
      const tsArr = [], priceArr = [];
      for (let i = 0; i < prices.length; i++) {
        if (!priceArr.length || !nearlyEqual(prices[i], priceArr[priceArr.length - 1])) {
          priceArr.push(prices[i]);
          tsArr.push(labels[i]);
        }
      }

      // enforce max
      const keepFrom = Math.max(0, priceArr.length - MAX_POINTS);
      const finalPrices = priceArr.slice(keepFrom);
      const finalTimestamps = tsArr.slice(keepFrom);

      // replace vs append
      const needFull = opts.forceFull || lastSelectedRangeKey !== selectedRangeKey;
      if (needFull) {
        chart.data.labels = finalPrices.map(() => "");
        chart.data.datasets[0].data = finalPrices;
        chart._timestamps = finalTimestamps;
        safeChartUpdate(chart);
      } else {
        const curData = chart.data.datasets[0].data.slice();
        const curTs = chart._timestamps.slice();
        const newPts = [];
        for (let i = 0; i < finalPrices.length; i++) {
          const ts = finalTimestamps[i];
          if (lastPlottedTs && ts <= lastPlottedTs) continue;
          const p = finalPrices[i];
          if (lastPlottedPrice != null && nearlyEqual(p, lastPlottedPrice)) continue;
          newPts.push({ ts, p });
        }
        newPts.forEach(pt => { curData.push(pt.p); curTs.push(pt.ts); });
        const overflow = Math.max(0, curData.length - MAX_POINTS);
        chart.data.datasets[0].data = overflow ? curData.slice(overflow) : curData;
        chart.data.labels = chart.data.datasets[0].data.map(() => "");
        chart._timestamps = overflow ? curTs.slice(overflow) : curTs;
        if (newPts.length) safeChartUpdate(chart);
      }

      lastPlottedTs = finalTimestamps[finalTimestamps.length - 1];
      lastPlottedPrice = finalPrices[finalPrices.length - 1];
      lastSelectedRangeKey = selectedRangeKey;

      ensureRangeControls(chart.canvas.parentElement || document.body);
    } catch (err) {
      if (err.name === "AbortError") {
        if (SHOW_WARNINGS) showDebug("Fetch aborted (stale request).", false);
      } else {
        showDebug("Update error: " + err.message, true);
        console.error(err);
      }
    } finally {
      isUpdating = false;
      currentAbort = null;
    }
  }

  // Entry
  async function start() {
    try {
      await loadScript(CHART_JS_CDN);
      const canvas = ensureContainerAndCanvas();
      const chart = createChartOnCanvas(canvas);
      window._chartInstance = chart;
      ensureRangeControls(canvas.parentElement || document.body);
      await updateChartFromJson(chart, { forceFull: true });
      pollIntervalId = setInterval(() => updateChartFromJson(chart), POLL_INTERVAL_MS);
      window.addEventListener("beforeunload", () => {
        if (pollIntervalId) clearInterval(pollIntervalId);
        if (currentAbort) currentAbort.abort();
      });
      showDebug(`Live chart started for "${DISPLAY_TICKER}" (default ${selectedRangeKey})`);
    } catch (err) {
      showDebug("Startup failed: " + err.message, true);
      console.error(err);
    }
  }

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", start);
  else
    start();
})();
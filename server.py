(() => {
  // -------- CONFIG --------
  let DISPLAY_TICKER = "Reliance";
  let DATA_URL = "../Company-Jsons/Reliance.json";
  const POLL_INTERVAL_MS = 10000;
  const MAX_POINTS = 200;
  const CHART_JS_CDN = "https://cdn.jsdelivr.net/npm/chart.js";
  const CANVAS_ID = "mainChart";
  const DEBUG_ID = "chartDebugOverlay";
  const SHOW_WARNINGS = false;
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
  let currentAbort = null;
  let pollIntervalId = null;
  let isUpdating = false;

  // ==============================
  // Debug Overlay
  // ==============================
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

  // ==============================
  // Script loader
  // ==============================
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

  // ==============================
  // Destroy old chart and stop polling
  // ==============================
  function destroyExistingChart() {
    if (pollIntervalId) { clearInterval(pollIntervalId); pollIntervalId = null; }
    if (currentAbort) { currentAbort.abort(); currentAbort = null; }
    if (window._chartInstance) {
      try { window._chartInstance.destroy(); } catch (e) { console.warn("Failed to destroy old chart:", e); }
      window._chartInstance = null;
    }
    const oldCanvas = document.getElementById(CANVAS_ID);
    if (oldCanvas) {
      const wrapper = oldCanvas.parentElement;
      if (wrapper && wrapper.classList.contains("chart-card")) { try { wrapper.remove(); } catch (e) { console.warn(e); } }
      else { try { oldCanvas.remove(); } catch (e) { console.warn(e); } }
    }
  }

  function ensureContainerAndCanvas() {
    let container = document.querySelector(".header_box_two") || document.body;

    const wrapper = document.createElement("div");
    wrapper.className = "chart-card";
    wrapper.id = "chartContainer";
    wrapper.style.width = "100%";
    wrapper.style.minHeight = "430px";
    wrapper.style.height = "440px";

    const title = document.createElement("h6");
    title.id = "chartTitle";
    title.style.fontFamily = "Orbitron, sans-serif";
    title.style.textAlign = "center";
    title.style.margin = "-19px 0";
    title.textContent = `Live Chart — ${DISPLAY_TICKER}`;
    wrapper.appendChild(title);

    const canvas = document.createElement("canvas");
    canvas.id = CANVAS_ID;
    canvas.style.width = "100%";
    canvas.style.height = "380px";
    wrapper.appendChild(canvas);

    container.appendChild(wrapper);
    return canvas;
  }

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

  function createChartOnCanvas(canvas) {
    const ctx = canvas.getContext("2d");
    const cfg = {
      type: "line",
      data: { labels: [], datasets: [{ data: [], borderColor: "#f59b0bff", backgroundColor: "#e0911251", borderWidth: 2, pointRadius: 2, pointHoverRadius: 3, pointBackgroundColor: "#fff", pointBorderColor: "#f59b0bff", pointBorderWidth: 2, tension: 0.1, fill: true }] },
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
        scales: { x: { display: false }, y: { ticks: { color: "#aaa" }, grid: { color: "rgba(255,255,255,0.08)" } } }
      }
    };
    const chart = new Chart(ctx, cfg);
    chart._timestamps = [];
    return chart;
  }

  function ensureRangeControls(container) {
    const parent = container.querySelector(".chart-card") || container;
    let controls = parent.querySelector(".chart-range-controls");
    if (!controls) {
      controls = document.createElement("div");
      controls.className = "chart-range-controls";
      controls.style.display = "flex";
      controls.style.gap = "6px";
      controls.style.marginBottom = "8px";
      parent.insertBefore(controls, parent.firstChild.nextSibling);
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
    if (!RANGE_OPTIONS.hasOwnProperty(key)) return;
    lastSelectedRangeKey = selectedRangeKey;
    selectedRangeKey = key;
    if (window._chartInstance) updateChartFromJson(window._chartInstance, { forceFull: true });
    try { localStorage.setItem("lastRange", key); } catch (_) { }
  }

  async function updateChartFromJson(chart, opts = { forceFull: false }) {
    if (isUpdating) return;
    isUpdating = true;
    try {
      if (currentAbort) currentAbort.abort();
      currentAbort = new AbortController();
      const json = await fetchJsonData(DATA_URL, currentAbort.signal);
      const matches = json.filter(e => e.ticker === DISPLAY_TICKER);
      if (!matches.length) return showDebug(`No entries for ticker "${DISPLAY_TICKER}".`, true);

      const normalized = matches.map(r => ({ row: r, tsMs: new Date(r.timestamp).getTime() }));
      const datasetLatestTs = Math.max(...normalized.map(n => n.tsMs || 0));
      let filtered = normalized;

      if (datasetLatestTs && RANGE_OPTIONS[selectedRangeKey] !== Infinity) {
        const cutoff = datasetLatestTs - RANGE_OPTIONS[selectedRangeKey];
        filtered = normalized.filter(n => n.tsMs && n.tsMs >= cutoff);
      }

      const labels = [], prices = [];
      filtered.sort((a, b) => a.tsMs - b.tsMs).forEach(item => {
        const p = parseFloat(item.row.price);
        if (isFinite(p)) { labels.push(item.tsMs); prices.push(p); }
      });

      if (!prices.length) return showDebug("No valid price data to plot.", true);

      const tsArr = [], priceArr = [];
      for (let i = 0; i < prices.length; i++) {
        if (!priceArr.length || !nearlyEqual(prices[i], priceArr[priceArr.length - 1])) {
          priceArr.push(prices[i]); tsArr.push(labels[i]);
        }
      }

      const keepFrom = Math.max(0, priceArr.length - MAX_POINTS);
      const finalPrices = priceArr.slice(keepFrom);
      const finalTimestamps = tsArr.slice(keepFrom);

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

      const parent = chart.canvas?.parentElement || document.body;
      ensureRangeControls(parent);

    } catch (err) {
      if (err.name !== "AbortError") showDebug("Update error: " + err.message, true);
    } finally { isUpdating = false; currentAbort = null; }
  }

  // ==============================
  // Start chart
  // ==============================
  async function start() {
    try {
      destroyExistingChart();
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
    } catch (err) { showDebug("Startup failed: " + err.message, true); }
  }

  // ==============================
  // Create JSON via server and start chart
  // ==============================
  async function createJsonAndStart(ticker, exchange = "NSE") {
    try {
      const resp = await fetch("/create-json", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ ticker, exchange })
      });
      const data = await resp.json();
      console.log(data.status || data.error);

      DISPLAY_TICKER = ticker;
      DATA_URL = `../Company-Jsons/${ticker}.json`;
      const title = document.getElementById("chartTitle");
      if (title) title.textContent = `Live Chart — ${DISPLAY_TICKER}`;

      await start(); // start chart polling
    } catch (err) { console.error("Error creating JSON:", err); }
  }

  // ==============================
  // Apply button logic
  // ==============================
  function setupApplyButton() {
    document.addEventListener("DOMContentLoaded", () => {
      const applyBtn = document.getElementById("applyBtn");
      const tickerInput = document.getElementById("tickerInput");
      const exchangeDisplay = document.getElementById("exchangeDisplay");
      const errorMsg = document.getElementById("errorMsg");
      if (!applyBtn || !tickerInput) return;

      tickerInput.addEventListener("keydown", (e) => { if (e.key === "Enter") { e.preventDefault(); applyBtn.click(); } });

      applyBtn.addEventListener("click", async () => {
        const ticker = tickerInput.value.trim().toUpperCase();
        if (!ticker) {
          if (errorMsg) { errorMsg.style.display = "block"; errorMsg.style.color = "red"; errorMsg.textContent = "⚠️ Please enter a ticker."; }
          return;
        }

        let exchange = "NASDAQ";
        if (ticker.match(/^(RELIANCE|TCS|INFY|HDFCBANK|AIRTEL|ICICI)$/)) exchange = "NSE";
        if (exchangeDisplay) exchangeDisplay.value = exchange;

        await createJsonAndStart(ticker, exchange);
      });
    });
  }

  setupApplyButton();
  start();
})();

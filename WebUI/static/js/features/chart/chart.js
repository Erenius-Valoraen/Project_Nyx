/**
 * Candle chart and trade entry lines.
 * Safe against duplicate API calls and rate limits.
 */

import * as api from '../../core/api.js';
import { onStateToUI } from '../../sync/uiSync.js';

/* ───────────────────────────────────── */
/* CONSTANTS */
/* ───────────────────────────────────── */

const TIMEFRAME_SECONDS = {
  ONE_MINUTE: 60,
  FIVE_MINUTE: 300,
  FIFTEEN_MINUTE: 900,
  ONE_HOUR: 3600,
  ONE_DAY: 86400,
};

const LTP_INTERVAL_MS = 1000;

/* ───────────────────────────────────── */
/* CHART SETUP */
/* ───────────────────────────────────── */

const container = document.getElementById('candle-chart');
if (!container) throw new Error('candle-chart element not found');

const chart = LightweightCharts.createChart(container, {
  width: container.clientWidth || 800,
  height: container.clientHeight || 400,
  layout: {
    background: { type: 'solid', color: '#0a0a0c' },
    textColor: '#8b8fa3',
    fontFamily: 'JetBrains Mono, Fira Code, monospace',
    fontSize: 12,
  },
  grid: {
    vertLines: { color: 'rgba(255,255,255,0.04)' },
    horzLines: { color: 'rgba(255,255,255,0.04)' },
  },
  crosshair: {
    mode: LightweightCharts.CrosshairMode.Normal,
  },
  timeScale: {
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 10,
    barSpacing: 8,
  },
});

const candlestickSeries = chart.addSeries(
  LightweightCharts.CandlestickSeries,
  {
    upColor: '#26a69a',
    downColor: '#ef5350',
    wickUpColor: '#26a69a',
    wickDownColor: '#ef5350',
    borderVisible: false,
  }
);

/* ───────────────────────────────────── */
/* STATE */
/* ───────────────────────────────────── */

let currentInstrument = null;
let currentTimeframe = 'ONE_MINUTE';

let historicalLoaded = false;
let candleFetchPromise = null;

let lastBar = null;
let didInitialFit = false;

let lastLtpCall = 0;

const tradeEntryLines = new Map();

/* ───────────────────────────────────── */
/* TRADE ENTRY LINES */
/* ───────────────────────────────────── */

function updateTradeEntryLines(positions) {
  if (!currentInstrument) return;

  const active = new Set();

  (positions || []).forEach((pos) => {
    if (!pos.is_open || pos.sym !== currentInstrument) return;

    active.add(pos.id);

    if (!tradeEntryLines.has(pos.id)) {
      const line = candlestickSeries.createPriceLine({
        price: pos.entry,
        color: pos.side === 'buy' ? '#26a69a' : '#ef5350',
        lineWidth: 2,
        axisLabelVisible: true,
      });
      tradeEntryLines.set(pos.id, line);
    } else {
      tradeEntryLines.get(pos.id).applyOptions({ price: pos.entry });
    }
  });

  tradeEntryLines.forEach((line, id) => {
    if (!active.has(id)) {
      candlestickSeries.removePriceLine(line);
      tradeEntryLines.delete(id);
    }
  });
}

/* ───────────────────────────────────── */
/* HISTORICAL CANDLES */
/* ───────────────────────────────────── */

export function loadCandlesForInstrument(instrument, timeframe = currentTimeframe) {
  if (!instrument) return;

  const instrumentChanged = instrument !== currentInstrument;
  const timeframeChanged = timeframe !== currentTimeframe;

  if (instrumentChanged || timeframeChanged) {
    currentInstrument = instrument;
    currentTimeframe = timeframe;

    historicalLoaded = false;
    candleFetchPromise = null;
    lastBar = null;
    didInitialFit = false;

    tradeEntryLines.forEach((l) => candlestickSeries.removePriceLine(l));
    tradeEntryLines.clear();
  }

  if (historicalLoaded || candleFetchPromise) return;

  candleFetchPromise = api
    .postCandles(instrument, timeframe)
    .then((candles) => {
      if (!Array.isArray(candles) || candles.length === 0) return;

      candles.sort((a, b) => a.time - b.time);
      candlestickSeries.setData(candles);

      const last = candles[candles.length - 1];
      lastBar = { ...last };

      historicalLoaded = true;

      requestAnimationFrame(() => {
        chart.fitContent();
        applyInitialViewport(candles);
        didInitialFit = true;
      });
    })
    .catch((err) => {
      console.error('Candle fetch failed:', err);
    })
    .finally(() => {
      candleFetchPromise = null;
    });
}

/* ───────────────────────────────────── */
/* LTP UPDATES */
/* ───────────────────────────────────── */

function updateLastBarWithLtp(contract) {
  if (!contract || !historicalLoaded || !lastBar) return;

  const nowMs = Date.now();
  if (nowMs - lastLtpCall < LTP_INTERVAL_MS) return;
  lastLtpCall = nowMs;

  api
    .postOptLtp({ contracts: [contract] })
    .then((res) => {
      const ltp = res?.data?.[contract];
      if (typeof ltp !== 'number') return;

      const tf = TIMEFRAME_SECONDS[currentTimeframe] || 60;
      const now = Math.floor(Date.now() / 1000);
      const bucket = Math.floor(now / tf) * tf;

      if (bucket > lastBar.time) {
        lastBar = {
          time: bucket,
          open: lastBar.close,
          high: ltp,
          low: ltp,
          close: ltp,
        };
        candlestickSeries.update(lastBar);
        return;
      }

      lastBar = {
        ...lastBar,
        close: ltp,
        high: Math.max(lastBar.high, ltp),
        low: Math.min(lastBar.low, ltp),
      };

      candlestickSeries.update(lastBar);
    })
    .catch(console.error);
}

/* ───────────────────────────────────── */
/* VIEWPORT */
/* ───────────────────────────────────── */

function applyInitialViewport(candles) {
  const total = candles.length;
  const visible = Math.min(10, total);
  chart.timeScale().setVisibleRange({
    from: candles[total - visible].time,
    to: candles[total - 1].time,
  });
}

/* ───────────────────────────────────── */
/* RESIZE */
/* ───────────────────────────────────── */

const ro = new ResizeObserver(([e]) => {
  if (!e.contentRect.width) return;
  chart.applyOptions(e.contentRect);
});
ro.observe(container);

/* ───────────────────────────────────── */
/* TIMEFRAME SWITCH */
/* ───────────────────────────────────── */

document.querySelectorAll('.tf-switcher button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tf-switcher button')
      .forEach((b) => b.classList.remove('active'));

    btn.classList.add('active');

    if (currentInstrument) {
      loadCandlesForInstrument(currentInstrument, btn.dataset.tf);
    }
  });
});

/* ───────────────────────────────────── */
/* STATE SYNC */
/* ───────────────────────────────────── */

function onState(state) {
  if (state.positions) updateTradeEntryLines(state.positions);
  if (!state.selected_contract) return;

  if (state.selected_contract !== currentInstrument) {
    loadCandlesForInstrument(state.selected_contract);
    return;
  }

  updateLastBarWithLtp(state.selected_contract);
}

export function init() {
  onStateToUI(onState);
}
/**
 * Candle chart and trade entry lines. Subscribes to state via uiSync callbacks.
 */

import * as api from '../../core/api.js';
import { onStateToUI } from '../../sync/uiSync.js';

const container = document.getElementById('candle-chart');
if (!container) {
  throw new Error('candle-chart element not found');
}

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
    vertLine: { color: 'rgba(255,255,255,0.15)', style: LightweightCharts.LineStyle.Dashed },
    horzLine: { color: 'rgba(255,255,255,0.15)', style: LightweightCharts.LineStyle.Dashed },
  },
  rightPriceScale: {
    borderColor: 'rgba(255,255,255,0.15)',
    textColor: '#8b8fa3',
  },
  timeScale: {
    borderColor: 'rgba(255,255,255,0.15)',
    timeVisible: true,
    secondsVisible: false,
    rightOffset: 10,
    barSpacing: 8,
  },
  handleScroll: { mouseWheel: true, pressedMouseMove: true },
  handleScale: { axisPressedMouseMove: true, mouseWheel: true, pinch: true },
  watermark: { visible: false },
});

const candlestickSeries = chart.addSeries(LightweightCharts.CandlestickSeries, {
  upColor: '#26a69a',
  downColor: '#ef5350',
  borderVisible: false,
  wickUpColor: '#26a69a',
  wickDownColor: '#ef5350',
});

let didInitialFit = false;
let currentInstrument = null;
let lastInstrument = null;
let currentTimeframe = 'ONE_MINUTE';
/** True after we've loaded historical candles for currentInstrument; prevents refetch. */
let historicalLoaded = false;
/** Last bar in the series; updated with LTP on each tick. */
let lastBar = null;
const tradeEntryLines = new Map();

function updateTradeEntryLines(positions) {
  if (!currentInstrument) return;
  const activeIds = new Set();

  (positions || []).forEach((pos) => {
    if (!pos.is_open || pos.entry == null || pos.sym !== currentInstrument) return;
    const id = pos.id;
    activeIds.add(id);

    if (!tradeEntryLines.has(id)) {
      const isBuy = pos.side === 'buy';
      const line = candlestickSeries.createPriceLine({
        price: pos.entry,
        color: isBuy ? '#26a69a' : '#ef5350',
        lineWidth: 2,
        axisLabelVisible: true,
        title: `${isBuy ? 'BUY' : 'SELL'} @ ${pos.entry}`,
      });
      tradeEntryLines.set(id, line);
    } else {
      tradeEntryLines.get(id).applyOptions({ price: pos.entry });
    }
  });

  tradeEntryLines.forEach((line, id) => {
    if (!activeIds.has(id)) {
      candlestickSeries.removePriceLine(line);
      tradeEntryLines.delete(id);
    }
  });
}

/**
 * Fetch historical candles only once per instrument. Subsequent updates use LTP.
 */
export function loadCandlesForInstrument(instrument, timeframe = currentTimeframe) {
  if (!instrument) return;

  const instrumentChanged = instrument !== lastInstrument;
  if (instrumentChanged) {
    tradeEntryLines.forEach((line) => candlestickSeries.removePriceLine(line));
    tradeEntryLines.clear();
    lastInstrument = instrument;
    historicalLoaded = false;
    lastBar = null;
  }

  const timeframeChanged = timeframe !== currentTimeframe;
  currentInstrument = instrument;
  currentTimeframe = timeframe;
  didInitialFit = false;

  if (timeframeChanged) {
    historicalLoaded = false;
    lastBar = null;
  }

  if (historicalLoaded) {
    return;
  }

  api.postCandles(instrument, timeframe).then((candles) => {
    if (!Array.isArray(candles) || candles.length === 0) return;
    candles.sort((a, b) => a.time - b.time);
    candlestickSeries.setData(candles);
    historicalLoaded = true;
    const last = candles[candles.length - 1];
    lastBar = { time: last.time, open: last.open, high: last.high, low: last.low, close: last.close };
    // Defer viewport so it runs after chart has real dimensions and has processed setData
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        chart.fitContent();
        applyInitialViewport(candles);
        didInitialFit = true;
      });
    });
  });
}

/**
 * Update the current last bar with LTP for the contract (no historical refetch).
 */
function updateLastBarWithLtp(contract) {
  if (!contract || !historicalLoaded || !lastBar) return;

  api.postOptLtp({ contracts: [contract] }).then((result) => {
    if (!result?.ok || !result?.data) return;
    const ltp = result.data[contract];
    if (ltp == null || typeof ltp !== 'number') return;

    const updated = {
      ...lastBar,
      close: ltp,
      high: Math.max(lastBar.high, ltp),
      low: Math.min(lastBar.low, ltp),
    };
    lastBar = updated;
    candlestickSeries.update(updated);
    // console.log('Chart LTP updated:', updated);
  }).catch((err) => console.error('Chart LTP update failed:', err));
}

function applyInitialViewport(candles) {
  if (!candles?.length) return;
  const total = candles.length;
  const visible = Math.min(10, total);
  chart.timeScale().setVisibleRange({
    from: candles[total - visible].time,
    to: candles[total].time - 1,
  });
}

const ro = new ResizeObserver((entries) => {
  entries.forEach((e) => {
    if (e.contentRect.width && e.contentRect.height) {
      chart.applyOptions(e.contentRect);
      const data = candlestickSeries.data();
      if (!didInitialFit && data && data.length > 0) {
        applyInitialViewport(data);
        didInitialFit = true;
      }
    }
  });
});
ro.observe(container);

document.querySelectorAll('.tf-switcher button').forEach((btn) => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.tf-switcher button').forEach((b) => b.classList.remove('active'));
    btn.classList.add('active');
    if (currentInstrument) loadCandlesForInstrument(currentInstrument, btn.dataset.tf);
  });
});

function onState(state) {
  if (state.positions) updateTradeEntryLines(state.positions);
  if (!state.selected_contract) return;

  if (state.selected_contract !== currentInstrument || !historicalLoaded) {
    loadCandlesForInstrument(state.selected_contract);
    updateLastBarWithLtp(state.selected_contract);

    // console.log(candlestickSeries.data());
  } else {
    updateLastBarWithLtp(state.selected_contract);
  }
}

export function init() {
  onStateToUI(onState);
}

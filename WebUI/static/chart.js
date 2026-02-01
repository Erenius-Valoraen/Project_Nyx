const container = document.getElementById("candle-chart");

/* ---------------- Chart ---------------- */

const chart = LightweightCharts.createChart(container, {
    width: 1,
    height: 1, // dummy, fixed by ResizeObserver

    layout: {
        background: {
            type: 'solid',
            color: '#0a0a0c',
        },
        textColor: '#8b8fa3',
        fontFamily: 'JetBrains Mono, Fira Code, monospace',
        fontSize: 12,
    },

    grid: {
        vertLines: { color: 'rgba(255, 255, 255, 0.04)' },
        horzLines: { color: 'rgba(255, 255, 255, 0.04)' },
    },

    crosshair: {
        mode: LightweightCharts.CrosshairMode.Normal,
        vertLine: {
            color: 'rgba(255, 255, 255, 0.15)',
            width: 1,
            style: LightweightCharts.LineStyle.Dashed,
        },
        horzLine: {
            color: 'rgba(255, 255, 255, 0.15)',
            width: 1,
            style: LightweightCharts.LineStyle.Dashed,
        },
    },

    rightPriceScale: {
        borderColor: 'rgba(255, 255, 255, 0.15)',
        textColor: '#8b8fa3',
    },
    timeScale: {
        borderColor: 'rgba(255, 255, 255, 0.15)',
        timeVisible: true,
        secondsVisible: false,
        rightOffset: 10,     // space for future candles
        barSpacing: 8,
    },

    handleScroll: {
        mouseWheel: true,
        pressedMouseMove: true,
    },

    handleScale: {
        axisPressedMouseMove: true,
        mouseWheel: true,
        pinch: true,
    },

    watermark: { visible: false },
});

/* ---------------- Series ---------------- */

const candlestickSeries = chart.addSeries(
    LightweightCharts.CandlestickSeries,
    {
        upColor: '#26a69a',
        downColor: '#ef5350',
        borderVisible: false,
        wickUpColor: '#26a69a',
        wickDownColor: '#ef5350',
    }
);


/* ---------------- Trade entry lines ---------------- */

const entryLines = new Map();

/**
 * Update trade entry markers
 * @param {Array} positions - positions from /api/state
 */
window.updateTradeEntryLines = function (positions) {
    // Remove lines that no longer exist
    for (const [id, line] of entryLines.entries()) {
        if (!positions.find(p => p.id === id && p.is_open)) {
            candlestickSeries.removePriceLine(line);
            entryLines.delete(id);
        }
    }

    // Add/update active positions
    for (const pos of positions) {
        if (!pos.is_open || pos.entry == null) continue;

        if (entryLines.has(pos.id)) continue;

        const line = candlestickSeries.createPriceLine({
            price: pos.entry,
            color: '#26a69a',              // terminal green
            lineWidth: 2,
            lineStyle: LightweightCharts.LineStyle.Solid,
            axisLabelVisible: true,
            title: `ENTRY ${pos.side.toUpperCase()}`,
        });

        entryLines.set(pos.id, line);
    }
};

/* ---------------- State ---------------- */

let didInitialFit = false;
let currentInstrument = null;
let currentTimeframe = "ONE_MINUTE";

/* ---------------- Resize handling ---------------- */

const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
        const { width, height } = entry.contentRect;

        if (width > 0 && height > 0) {
            chart.applyOptions({ width, height });

            if (!didInitialFit && candlestickSeries.data()) {
                applyInitialViewport(candlestickSeries.data());
                didInitialFit = true;
            }
        }
    }
});

ro.observe(container);

window.addEventListener("resize", () => {
    chart.applyOptions({
        width: container.clientWidth,
        height: container.clientHeight,
    });
});

/* ---------------- Candle loading ---------------- */

window.loadCandlesForInstrument = async function (
    instrument,
    timeframe = currentTimeframe
) {
    if (!instrument) return;

    currentInstrument = instrument;
    currentTimeframe = timeframe;
    didInitialFit = false;

    const res = await fetch("/api/candles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            instrument,
            timeframe,
        }),
    });

    const candles = await res.json();
    candles.sort((a, b) => a.time - b.time);

    candlestickSeries.setData(candles);
    // applyInitialViewport(candles);
};

/* ---------------- Initial viewport logic ---------------- */

function applyInitialViewport(candles) {
    if (!candles || !candles.length) return;

    const total = candles.length;
    const visibleBars = Math.min(120, total); // default window

    const from = candles[total - visibleBars].time;
    const to = candles[total - 1].time + 10; // future space

    chart.timeScale().setVisibleRange({ from, to });
}

/* ---------------- Timeframe switcher ---------------- */

document.querySelectorAll(".tf-switcher button").forEach(btn => {
    btn.addEventListener("click", () => {
        document
            .querySelectorAll(".tf-switcher button")
            .forEach(b => b.classList.remove("active"));

        btn.classList.add("active");

        const tf = btn.dataset.tf;

        if (currentInstrument) {
            loadCandlesForInstrument(currentInstrument, tf);
        }
    });
});
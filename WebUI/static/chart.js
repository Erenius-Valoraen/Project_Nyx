const container = document.getElementById("candle-chart");

/* ---------------- Chart ---------------- */

const chart = LightweightCharts.createChart(container, {
    width: 1,
    height: 1,

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

/* ---------------- State ---------------- */

let didInitialFit = false;
let currentInstrument = null;
let lastInstrument = null;
let currentTimeframe = "ONE_MINUTE";

/* ---------------- Trade Entry Lines ---------------- */

const tradeEntryLines = new Map();

window.updateTradeEntryLines = function (positions) {
    if (!currentInstrument) return;

    const activeIds = new Set();

    for (const pos of positions) {
        if (!pos.is_open || pos.entry == null) continue;
        if (pos.sym !== currentInstrument) continue;

        const id = pos.id;
        activeIds.add(id);

        if (!tradeEntryLines.has(id)) {
            const isBuy = pos.side === "buy";

            const line = candlestickSeries.createPriceLine({
                price: pos.entry,
                color: isBuy ? "#26a69a" : "#ef5350",
                lineWidth: 2,
                axisLabelVisible: true,
                title: `${isBuy ? "BUY" : "SELL"} @ ${pos.entry}`,
            });

            tradeEntryLines.set(id, line);
        } else {
            tradeEntryLines.get(id).applyOptions({ price: pos.entry });
        }
    }

    // remove stale lines
    for (const [id, line] of tradeEntryLines.entries()) {
        if (!activeIds.has(id)) {
            candlestickSeries.removePriceLine(line);
            tradeEntryLines.delete(id);
        }
    }
};

/* ---------------- Candle loading ---------------- */

window.loadCandlesForInstrument = async function (
    instrument,
    timeframe = currentTimeframe
) {
    if (!instrument) return;

    // ✅ clear lines ONLY if instrument actually changed
    if (instrument !== lastInstrument) {
        for (const line of tradeEntryLines.values()) {
            candlestickSeries.removePriceLine(line);
        }
        tradeEntryLines.clear();
        lastInstrument = instrument;
    }

    currentInstrument = instrument;
    currentTimeframe = timeframe;
    didInitialFit = false;

    const res = await fetch("/api/candles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ instrument, timeframe }),
    });

    const candles = await res.json();
    candles.sort((a, b) => a.time - b.time);

    candlestickSeries.setData(candles);
};

/* ---------------- Initial viewport ---------------- */

function applyInitialViewport(candles) {
    if (!candles?.length) return;

    const total = candles.length;
    const visible = Math.min(120, total);

    chart.timeScale().setVisibleRange({
        from: candles[total - visible].time,
        to: candles[total - 1].time + 10,
    });
}

/* ---------------- Resize ---------------- */

const ro = new ResizeObserver(entries => {
    for (const e of entries) {
        if (e.contentRect.width && e.contentRect.height) {
            chart.applyOptions(e.contentRect);
            if (!didInitialFit && candlestickSeries.data()) {
                applyInitialViewport(candlestickSeries.data());
                didInitialFit = true;
            }
        }
    }
});

ro.observe(container);

/* ---------------- Timeframe switch ---------------- */

document.querySelectorAll(".tf-switcher button").forEach(btn => {
    btn.addEventListener("click", () => {
        document.querySelectorAll(".tf-switcher button")
            .forEach(b => b.classList.remove("active"));
        btn.classList.add("active");

        if (currentInstrument) {
            loadCandlesForInstrument(currentInstrument, btn.dataset.tf);
        }
    });
});
const container = document.getElementById("candle-chart");

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
        rightOffset: 10,     // 🔥 space for future candles
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

let didInitialFit = false;

/* ---------------- Resize handling ---------------- */

const ro = new ResizeObserver(entries => {
    for (const entry of entries) {
        const { width, height } = entry.contentRect;

        if (width > 0 && height > 0) {
            chart.applyOptions({ width, height });

            if (!didInitialFit) {
                applyInitialViewport(candlestickSeries)
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

/* ---------------- Historical candles ---------------- */

window.loadCandlesForInstrument = async function (instrument) {
    if (!instrument) return;

    const res = await fetch("/api/candles", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            instrument: instrument,
            timeframe: "ONE_MINUTE",
        }),
    });

    const candles = await res.json();

    candles.sort((a, b) => a.time - b.time);

    candlestickSeries.setData(candles);
    // chart.timeScale().fitContent();
};




function applyInitialViewport(candles) {
    if (!candles.length) return;

    const total = candles.length;
    const visibleBars = Math.min(120, total); // ~2 hours on 1m chart

    const from = candles[total - visibleBars].time;
    const to = candles[total + 10].time;

    chart.timeScale().setVisibleRange({
        from,
        to,
    });
}
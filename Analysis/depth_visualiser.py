import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
from matplotlib.colors import TwoSlopeNorm

# -------------------------
# CONFIG
# -------------------------
CSV_PATH = "../depth_history/log.csv"
TICK_SIZE = 0.05

# -------------------------
# LOAD DATA
# -------------------------
df = pd.read_csv(
    CSV_PATH,
    names=[
        "timestamp",
        "symbol",
        "bid_price",
        "bid_qty",
        "ask_price",
        "ask_qty",
        "vol_1s",
        "avg_vol_60s"
    ],
    parse_dates=["timestamp"]
)

df = df.sort_values("timestamp").reset_index(drop=True)

# Convert timestamps to seconds from start
t0 = df["timestamp"].iloc[0]
df["t"] = (df["timestamp"] - t0).dt.total_seconds()

# -------------------------
# BUILD PRICE GRID
# -------------------------
min_price = df[["bid_price", "ask_price"]].min().min()
max_price = df[["bid_price", "ask_price"]].max().max()

price_levels = np.arange(
    min_price - TICK_SIZE,
    max_price + TICK_SIZE,
    TICK_SIZE
)

price_to_idx = {p: i for i, p in enumerate(price_levels)}

# -------------------------
# BUILD HEATMAP MATRIX
# -------------------------
heatmap = np.zeros((len(price_levels), len(df)))

for i, row in df.iterrows():
    # Bid side (positive)
    bid_idx = price_to_idx.get(round(row.bid_price, 2))
    if bid_idx is not None:
        heatmap[bid_idx, i] += row.bid_qty

    # Ask side (negative)
    ask_idx = price_to_idx.get(round(row.ask_price, 2))
    if ask_idx is not None:
        heatmap[ask_idx, i] -= row.ask_qty

# -------------------------
# PLOT
# -------------------------
fig, ax = plt.subplots(figsize=(14, 6))

norm = TwoSlopeNorm(
    vmin=-np.nanmax(np.abs(heatmap)),
    vcenter=0,
    vmax=np.nanmax(np.abs(heatmap))
)

im = ax.imshow(
    heatmap,
    aspect="auto",
    origin="lower",
    cmap="RdBu_r",
    norm=norm
)

# Y-axis: price levels
ax.set_yticks(np.arange(len(price_levels))[::2])
ax.set_yticklabels([f"{p:.2f}" for p in price_levels[::2]])

# X-axis: time
ax.set_xlabel("Time (seconds)")
ax.set_ylabel("Price")

# Colorbar
cbar = plt.colorbar(im, ax=ax)
cbar.set_label("Queue Size (Bid + / Ask −)")

ax.set_title("Order Book Queue Persistence Heatmap")

plt.tight_layout()
plt.show()
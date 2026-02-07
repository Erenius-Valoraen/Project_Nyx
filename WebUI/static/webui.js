async function fetchJson(url, options) {
  const res = await fetch(url, options);
  const text = await res.text();
  try {
    return { ok: res.ok, status: res.status, data: JSON.parse(text) };
  } catch {
    return { ok: res.ok, status: res.status, data: text };
  }
}

function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined) return "-";
  return Number(num).toFixed(decimals);
}

/**
 * @param {string} message - The text to display
 * @param {string} type - 'success', 'error', 'warning', or 'info'
 * @param {number} duration - Time in ms before it disappears
 */
function showToast(message, type = 'info', duration = 3000) {
  let container = document.querySelector('.notification-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notification-container';
    document.body.appendChild(container);
  }

  const toast = document.createElement('div');
  // Dynamic class assignment: "notification success", etc.
  toast.className = `notification ${type}`;
  
  // Adding a terminal-style timestamp and prompt
  const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  toast.innerHTML = `<span style="opacity: 0.5">[${time}]</span> > ${message}`;

  container.appendChild(toast);

  // Trigger animation
  requestAnimationFrame(() => {
    toast.classList.add('show');
  });

  const removeToast = () => {
    toast.classList.remove('show');
    toast.addEventListener('transitionend', () => toast.remove());
  };

  const autoHide = setTimeout(removeToast, duration);

  toast.onclick = () => {
    clearTimeout(autoHide);
    removeToast();
  };
}

function formatPL(pl) {
  if (pl === null || pl === undefined) return "-";
  const val = Number(pl);
  const formatted = val.toLocaleString("en-US", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return val >= 0 ? `+${formatted}` : formatted;
}

function getSideClass(side) {
  if (side === "buy") return "side-buy";
  if (side === "sell") return "side-sell";
  return "side-flat";
}

function getPLClass(pl) {
  if (pl === null || pl === undefined) return "";
  return Number(pl) >= 0 ? "pl-positive" : "pl-negative";
}

function updatePositionsTable(data) {
  const tbody = document.getElementById("positions-tbody");
  if (!tbody) return;

  if (!data.positions || data.positions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" class="no-data">No open positions</td></tr>';
    return;
  }

  // 🔽 NEW: sort so latest trade is at the top
  const sortedPositions = [...data.positions].sort((a, b) => {
    // Prefer id-based ordering (newer id first)
    if (a.id != null && b.id != null) {
      return b.id - a.id;
    }
    return 0;
  });

  tbody.innerHTML = sortedPositions.map(pos => {
    const sideClass = getSideClass(pos.side);
    const openPLClass = getPLClass(pos.open_pl);
    const closedPLClass = getPLClass(pos.closed_pl);
    const statusClass = pos.is_open ? "status-open" : "status-closed";
    const statusText = pos.is_open ? "OPEN" : "CLOSED";

    return `
      <tr>
        <td>${pos.id ?? "-"}</td>
        <td>${pos.sym ?? "-"}</td>
        <td class="${sideClass}">${pos.side.toUpperCase()}</td>
        <td>${pos.orig_qty ?? "-"}</td>
        <td>${pos.open_qty ?? "-"}</td>
        <td>${formatNumber(pos.entry)}</td>
        <td>${formatNumber(pos.bid)}</td>
        <td>${formatNumber(pos.ask)}</td>
        <td>${formatNumber(pos.ltp)}</td>
        <td class="${openPLClass}">${formatPL(pos.open_pl)}</td>
        <td class="${closedPLClass}">${formatPL(pos.closed_pl)}</td>
        <td class="${statusClass}">${statusText}</td>
      </tr>
    `;
  }).join("");
}

/**
 * Parse available contracts from HTML:
 * Available: NIFTY, BANKNIFTY, RELIANCE
 */
function getContractsFromHint() {
  const hint = document.querySelector(".command-hint");
  if (!hint) return [];
  const text = hint.textContent || "";
  const match = text.match(/Available:\s*(.*)/i);
  if (!match) return [];
  return match[1].split(",").map(s => s.trim()).filter(Boolean);
}

async function refreshState() {
  try {
    const r = await fetchJson("/api/state");
    if (r.ok && r.data) {
      updatePositionsTable(r.data);

      // Update trade entry lines on chart
      if (window.updateTradeEntryLines && r.data.positions) {
        window.updateTradeEntryLines(r.data.positions);
      }

      // update active contract label in header
      const active = document.getElementById("active-contract");
      if (active) {
        active.textContent = r.data.selected_contract || "-";
      }
      // load candle data
      if (r.data.selected_contract && window.loadCandlesForInstrument) {
        window.loadCandlesForInstrument(r.data.selected_contract);
      }
    }
  } catch (error) {
    console.error("Failed to refresh state:", error);
  }
}

async function placeOrder(side, quantity) {
  if (quantity <= 0) {
    alert("Quantity must be greater than 0");
    return;
  }

  try {
    const r = await fetchJson("/api/order", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ quantity, side }),
    });

    if (r.ok && r.data.ok) {
      await refreshState();
      const qtyInput = document.getElementById("qty-input");
      if (qtyInput) {
        if (side === "buy") {
          showToast(`Bought ${quantity} qty`, 'success')
        }
        else if (side === "sell") {
          showToast(`Sold ${quantity} qty`, 'error')
        }
      };
    } else {
      if (side === "buy") {
          showToast(`Failed to buy ${quantity} qty`, 'error')
        }
        else if (side === "sell") {
          showToast(`Failed to buy ${quantity} qty`, 'error')
        }
      console.log(`Order failed: ${r.data.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Failed to place order:", error);
    alert("Failed to place order. Check console for details.");
  }
  refreshState()
}

async function testButton() {
  try {
    const r = await fetchJson("/api/opt_ltp", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ 
        "contract": "NIFTY03FEB2625600CE"
      }),
    });
    if (r.ok && r.data) {
      console.log(r.data)
    }
    

  }
  catch (error) {
    console.error(error)
  }
}

async function switchContract(symbol) {
  try {
    const r = await fetchJson("/api/select_contract", {
      method: "POST",
      headers: { "content-type": "application/json" },
      body: JSON.stringify({ symbol }),
    });

    if (r.ok && r.data.ok) {
      await refreshState();
      if (window.loadCandlesForInstrument) {
        window.loadCandlesForInstrument(symbol);
      }
    } else {
      alert(`Contract switch failed: ${r.data.error || "Unknown error"}`);
    }
  } catch (error) {
    console.error("Failed to switch contract:", error);
    alert("Failed to switch contract. Check console for details.");
  }
}

function handleCommandBar(event) {
  if (event.key !== "Enter") return;

  const input = event.target;
  const command = input.value.trim();
  input.value = "";

  if (!command) return;

  const parts = command.split(/\s+/);
  if (parts.length !== 2) {
    alert("Usage:\n buy <qty>\n sell <qty>\n use <symbol|index>");
    return;
  }

  const [cmd, arg] = parts;

  if (cmd.toLowerCase() === "use") {
    // allow use 1, use 2, or use SYMBOL
    const idx = parseInt(arg, 10);
    if (!isNaN(idx)) {
      const contracts = getContractsFromHint();
      const symbol = contracts[idx - 1];
      if (!symbol) {
        alert("Invalid contract index");
        return;
      }
      switchContract(symbol);
      return;
    }

    switchContract(arg);
    return;
  }

  const side = cmd.toLowerCase();
  if (side !== "buy" && side !== "sell") {
    alert("Invalid side. Use 'buy' or 'sell'");
    return;
  }

  const qty = parseInt(arg, 10);
  if (isNaN(qty) || qty <= 0) {
    alert("Invalid quantity");
    return;
  }

  placeOrder(side, qty);
}

document.addEventListener("DOMContentLoaded", () => {
  const buyBtn = document.getElementById("buy-btn");
  const sellBtn = document.getElementById("sell-btn");
  const testBtn = document.getElementById("test-btn")
  const qtyInput = document.getElementById("qty-input");
  const commandInput = document.getElementById("command-input");

  // Button events
  if (buyBtn) buyBtn.addEventListener("click", () => placeOrder("buy", parseInt(qtyInput.value, 10)));
  if (sellBtn) sellBtn.addEventListener("click", () => placeOrder("sell", parseInt(qtyInput.value, 10)));
  if (testBtn) testBtn.addEventListener("click", () => testButton())
  if (commandInput) commandInput.addEventListener("keydown", handleCommandBar);

  // Initial load and periodic refresh
  refreshState();
  setInterval(refreshState, 1000);
});
function switchView(viewName) {
  document.querySelectorAll(".view").forEach(v => v.classList.remove("active"));
  document.getElementById(`view-${viewName}`).classList.add("active");
}

function toggleFullscreen() {
  const full = document.querySelector(".fullscreen");
  if (full) full.classList.remove("fullscreen");
  document.querySelector(".terminal-container").classList.add("fullscreen");
}

function focusAtEnd(el) {
  el.focus({ preventScroll: true });
  const len = el.value.length;
  el.setSelectionRange(len, len);
}

document.addEventListener("DOMContentLoaded", () => {
  const qty_input = document.querySelector("#qty-input");
  const command_input = document.querySelector("#command-input");

  switchView("trade");

  /* ===============================
     🔢 QTY INPUT: NUMERIC ONLY
  =============================== */
  qty_input.addEventListener("keydown", e => {
    const allowed =
      (e.key >= "0" && e.key <= "9") ||
      ["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key);

    if (!allowed) e.preventDefault();
  });

  /* ===============================
     ⌨️ GLOBAL KEY HANDLER
  =============================== */
  document.addEventListener("keydown", (e) => {
    const active = document.activeElement;
    const qtyFocused = active === qty_input;
    const commandFocused = active === command_input;

    /* ---------- TAB = TOGGLE QTY ---------- */
    if (e.key === "Tab") {
      e.preventDefault();

      if (qtyFocused) {
        qty_input.blur();          // 🔴 unfocus
      } else {
        focusAtEnd(qty_input);     // 🟢 focus
      }
      return;
    }

    /* ---------- BUY / SELL HOTKEYS ---------- */
    if (!commandFocused) {
      if (e.key === "b") {
        e.preventDefault();
        placeOrder("buy", parseInt(qty_input.value || 0, 10));
        return;
      }

      if (e.key === "s") {
        e.preventDefault();
        placeOrder("sell", parseInt(qty_input.value || 0, 10));
        return;
      }
    }

    /* ---------- BLOCK OTHER HOTKEYS WHILE TYPING COMMAND ---------- */
    if (commandFocused) return;

    /* ---------- VIEWS ---------- */
    if (e.key === "1") switchView("trade");
    if (e.key === "2") switchView("chart");
    if (e.key === "f") toggleFullscreen();
  });
});
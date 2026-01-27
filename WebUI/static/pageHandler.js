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
  el.focus();
  const len = el.value.length;
  el.setSelectionRange(len, len);
}

document.addEventListener("DOMContentLoaded", () => {
  const qty_input = document.querySelector("#qty-input");
  const order_bar = document.querySelector("#command-input");

  switchView("trade");

  // 🔒 Numeric-only safety net
  qty_input.addEventListener("input", () => {
    qty_input.value = qty_input.value.replace(/\D/g, "");
  });

  document.addEventListener("keydown", (e) => {
    const el = document.activeElement;
    const isTyping =
      el.tagName === "INPUT" ||
      el.tagName === "TEXTAREA" ||
      el.isContentEditable;

    // ---- ORDERS ----
    if (e.key === "b" && !isTyping) {
      placeOrder("buy", parseInt(qty_input.value || 0, 10));
    }

    if (e.key === "s" && !isTyping) {
      placeOrder("sell", parseInt(qty_input.value || 0, 10));
    }

    // ---- VIEWS ----
    if (e.key === "1" && !isTyping) switchView("trade");
    if (e.key === "2" && !isTyping) switchView("chain");
    if (e.key === "f" && !isTyping) toggleFullscreen();

    // ---- TAB TOGGLE (FOCUS / BLUR) ----
    if (e.key === "Tab") {
      e.preventDefault();

      if (document.activeElement === qty_input) {
        qty_input.blur();               // 🔴 unfocus
      } else {
        focusAtEnd(qty_input);          // 🟢 focus at end
      }
    }
  });
});
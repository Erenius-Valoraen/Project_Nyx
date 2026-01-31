function switchView(viewName) {
  $(".view").removeClass("active");
  $(`#view-${viewName}`).addClass("active");
}

function toggleFullscreen() {
  $(".terminal-container").toggleClass("fullscreen");
}

function focusAtEnd($el) {
  const el = $el[0];
  el.focus({ preventScroll: true });
  const len = el.value.length;
  el.setSelectionRange(len, len);
}

$(document).ready(function () {
  const $qtyInput = $("#qty-input");
  const $commandInput = $("#command-input");

  switchView("trade");

  /* ===============================
     🔢 QTY INPUT: NUMERIC ONLY
  =============================== */
  $qtyInput.on("keydown", function (e) {
    const allowed =
      (e.key >= "0" && e.key <= "9") ||
      ["Backspace", "Delete", "ArrowLeft", "ArrowRight", "Home", "End"].includes(e.key);

    if (!allowed) e.preventDefault();
  });

  /* ===============================
     ⌨️ GLOBAL KEY HANDLER
  =============================== */
  $(document).on("keydown", function (e) {
    const active = document.activeElement;
    const qtyFocused = active === $qtyInput[0];
    const commandFocused = active === $commandInput[0];

    /* ---------- TAB = TOGGLE QTY ---------- */
    if (e.key === "Tab") {
      e.preventDefault();

      if (qtyFocused) {
        $qtyInput.blur();
      } else {
        focusAtEnd($qtyInput);
      }
      return;
    }

    /* ---------- BUY / SELL HOTKEYS ---------- */
    if (!commandFocused) {
      if (e.key === "b") {
        e.preventDefault();
        placeOrder("buy", parseInt($qtyInput.val() || 0, 10));
        return;
      }

      if (e.key === "s") {
        e.preventDefault();
        placeOrder("sell", parseInt($qtyInput.val() || 0, 10));
        return;
      }
    }

    /* ---------- BLOCK OTHER HOTKEYS WHILE TYPING ---------- */
    if (commandFocused || qtyFocused) return;

    /* ---------- VIEWS ---------- */
    if (e.key === "1") switchView("trade");
    if (e.key === "2") switchView("chart");
    if (e.key === "f") toggleFullscreen();
  });
});
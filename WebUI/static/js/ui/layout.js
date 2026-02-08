/**
 * Layout: fullscreen toggle, focus helpers, qty input numeric-only.
 */

export function toggleFullscreen() {
  const container = document.querySelector('.terminal-container');
  if (container) container.classList.toggle('fullscreen');
}

export function focusAtEnd(el) {
  if (!el) return;
  el.focus({ preventScroll: true });
  const len = (el.value || '').length;
  el.setSelectionRange(len, len);
}

export function init() {
  const qtyInput = document.getElementById('qty-input');
  if (qtyInput) {
    qtyInput.addEventListener('keydown', (e) => {
      const allowed =
        (e.key >= '0' && e.key <= '9') ||
        ['Backspace', 'Delete', 'ArrowLeft', 'ArrowRight', 'Home', 'End'].includes(e.key);
      if (!allowed) e.preventDefault();
    });
  }
}

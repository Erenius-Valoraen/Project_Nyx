/**
 * Global hotkeys: 1/2 views, b/s buy/sell, f fullscreen, Tab qty focus.
 */

import { switchView } from './views.js';
import { toggleFullscreen, focusAtEnd } from './layout.js';
import { placeOrder } from '../features/trading/orders.js';

export function init() {
  const qtyInput = document.getElementById('qty-input');
  const commandInput = document.getElementById('command-input');

  document.addEventListener('keydown', (e) => {
    const active = document.activeElement;
    const qtyFocused = active === qtyInput;
    const commandFocused = active === commandInput;

    if (e.key === 'Tab') {
      e.preventDefault();
      if (qtyFocused) qtyInput?.blur();
      else focusAtEnd(qtyInput);
      return;
    }

    if (!commandFocused && (e.key === 'b' || e.key === 's')) {
      e.preventDefault();
      const qty = parseInt(qtyInput?.value || 0, 10);
      placeOrder(e.key === 'b' ? 'buy' : 'sell', qty);
      return;
    }

    if (commandFocused || qtyFocused) return;

    if (e.key === '1') switchView('trade');
    if (e.key === '2') switchView('chart');
    if (e.key === 'f') toggleFullscreen();
  });
}

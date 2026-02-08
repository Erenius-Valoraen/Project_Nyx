/**
 * All user input: buttons, command bar, hotkeys, layout/views.
 * Single place to wire every DOM interaction.
 */

import { init as initLayout } from './layout.js';
import { init as initViews } from './views.js';
import { init as initHotkeys } from './hotkeys.js';
import { init as initCommandBar } from '../features/trading/commandBar.js';
import { placeOrder } from '../features/trading/orders.js';
import * as api from '../core/api.js';
import * as chart from '../features/chart/chart.js';

export function init() {
  initLayout();
  initViews();
  initHotkeys();
  initCommandBar(document.getElementById('command-input'));

  // Inputs for trading
  const buyBtn = document.getElementById('buy-btn');
  const sellBtn = document.getElementById('sell-btn');
  const testBtn = document.getElementById('test-btn');
  const qtyInput = document.getElementById('qty-input');

  if (buyBtn && qtyInput) {
    buyBtn.addEventListener('click', () => placeOrder('buy', parseInt(qtyInput.value, 10) || 0));
  }
  if (sellBtn && qtyInput) {
    sellBtn.addEventListener('click', () => placeOrder('sell', parseInt(qtyInput.value, 10) || 0));
  }
  if (testBtn) {
    testBtn.addEventListener('click', () => {
      api.postOptLtp({ contract: 'NIFTY03FEB2625600CE' }).then(console.log).catch(console.error);
    });
  }

}

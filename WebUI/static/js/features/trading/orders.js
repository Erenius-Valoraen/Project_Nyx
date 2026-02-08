/**
 * Order placement and contract selection. Calls API then refreshes state.
 */

import * as api from '../../core/api.js';
import { refresh } from '../../sync/stateSync.js';
import { showToast } from '../../core/utils.js';

export function placeOrder(side, quantity) {
  if (quantity <= 0) {
    alert('Quantity must be greater than 0');
    return;
  }
  api.postOrder({ quantity, side }).then((r) => {
    if (r.ok && r.data && r.data.ok) {
      refresh();
      showToast(side === 'buy' ? `Bought ${quantity} qty` : `Sold ${quantity} qty`, side === 'buy' ? 'success' : 'error');
    } else {
      showToast(`Failed to ${side} ${quantity} qty`, 'error');
      console.log('Order failed:', (r.data && r.data.error) || 'Unknown error');
    }
  }).catch((err) => {
    console.error('Failed to place order:', err);
    alert('Failed to place order. Check console for details.');
  });
  refresh();
}

export function switchContract(symbol) {
  api.postSelectContract(symbol).then((r) => {
    if (r.ok && r.data && r.data.ok) {
      refresh();
    } else {
      alert(`Contract switch failed: ${(r.data && r.data.error) || 'Unknown error'}`);
    }
  }).catch((err) => {
    console.error('Failed to switch contract:', err);
    alert('Failed to switch contract. Check console for details.');
  });
}

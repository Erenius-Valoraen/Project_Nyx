/**
 * State → UI. Subscribes to state and updates the DOM (positions table, active contract, chart lines).
 */

import { getState, subscribe } from '../core/state.js';
import { formatNumber, formatPL, getSideClass, getPLClass } from '../core/utils.js';

function renderPositions(positions) {
  const tbody = document.getElementById('positions-tbody');
  if (!tbody) return;
  if (!positions || positions.length === 0) {
    tbody.innerHTML = '<tr><td colspan="12" class="no-data">No open positions</td></tr>';
    return;
  }
  const sorted = [...positions].sort((a, b) => (b.id != null && a.id != null ? b.id - a.id : 0));
  tbody.innerHTML = sorted
    .map((pos) => {
      const sideClass = getSideClass(pos.side);
      const openPLClass = getPLClass(pos.open_pl);
      const closedPLClass = getPLClass(pos.closed_pl);
      const statusClass = pos.is_open ? 'status-open' : 'status-closed';
      const statusText = pos.is_open ? 'OPEN' : 'CLOSED';
      return `<tr>
        <td>${pos.id ?? '-'}</td>
        <td>${pos.sym ?? '-'}</td>
        <td class="${sideClass}">${(pos.side || '').toUpperCase()}</td>
        <td>${pos.orig_qty ?? '-'}</td>
        <td>${pos.open_qty ?? '-'}</td>
        <td>${formatNumber(pos.entry)}</td>
        <td>${formatNumber(pos.bid)}</td>
        <td>${formatNumber(pos.ask)}</td>
        <td>${formatNumber(pos.ltp)}</td>
        <td class="${openPLClass}">${formatPL(pos.open_pl)}</td>
        <td class="${closedPLClass}">${formatPL(pos.closed_pl)}</td>
        <td class="${statusClass}">${statusText}</td>
      </tr>`;
    })
    .join('');
}

function renderActiveContract(selected_contract) {
  const el = document.getElementById('active-contract');
  if (el) el.textContent = selected_contract || '-';
}

/** Callbacks registered by features that need state (e.g. chart for entry lines + candles). */
const stateToUICallbacks = [];

export function onStateToUI(fn) {
  if (typeof fn === 'function') stateToUICallbacks.push(fn);
}

function notifyCallbacks(state) {
  stateToUICallbacks.forEach((fn) => fn(state));
}

function sync(state) {
  renderPositions(state.positions);
  renderActiveContract(state.selected_contract);
  notifyCallbacks(state);
}

export function init() {
  sync(getState());
  subscribe(sync);
}

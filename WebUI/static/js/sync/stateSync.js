/**
 * Data → state. API responses are written into the single state store.
 */

import * as api from '../core/api.js';
import { setState } from '../core/state.js';
import { refresh as pollRefresh } from '../core/poller.js';

export function pushStateFromApi(data) {
  if (data && typeof data === 'object') setState(data);
}

export async function refreshState() {
  const r = await api.getState();
  if (r.ok && r.data) setState(r.data);
  return r;
}

/** Call after mutations (order, select contract) so UI updates immediately; poller keeps it fresh. */
export function refresh() {
  return pollRefresh();
}

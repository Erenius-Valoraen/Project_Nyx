/**
 * Refresh loop: fetches state from API and pushes into app state. Very important for live UI.
 */

import * as api from './api.js';
import { setState } from './state.js';

const POLL_INTERVAL_MS = 1000;
let timerId = null;

export function refresh() {
  return api.getState().then((r) => {
    if (r.ok && r.data) setState(r.data);
    return r;
  }).catch((err) => {
    console.error('Poll failed:', err);
  });
}

export function start() {
  if (timerId) return;
  refresh();
  timerId = setInterval(refresh, POLL_INTERVAL_MS);
}

export function stop() {
  if (timerId) {
    clearInterval(timerId);
    timerId = null;
  }
}

export function getPollIntervalMs() {
  return POLL_INTERVAL_MS;
}

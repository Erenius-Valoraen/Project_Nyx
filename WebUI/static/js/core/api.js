/**
 * All HTTP endpoints in one place. Uses transport (fetch/ws abstraction).
 */

import { get, post } from './transport.js';

export function getState() {
  return get('/api/state');
}

export function postOrder(payload) {
  return post('/api/order', payload);
}

export function postSelectContract(symbol) {
  return post('/api/select_contract', { symbol });
}

export function getNiftyLtp() {
  return get('/api/nifty_ltp').then((r) => (r.ok ? r.data : null));
}

/** @param {{ contract?: string, contracts?: string[] }} payload */
export function postOptLtp(payload) {
  return post('/api/opt_ltp', payload).then((r) => r.data);
}

export function postCandles(instrument, timeframe = 'ONE_MINUTE') {
  return post('/api/candles', { instrument, timeframe }).then((r) => (r.ok ? r.data : null));
}

export function getHealth() {
  return get('/api/health');
}

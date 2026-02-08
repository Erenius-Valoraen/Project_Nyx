/**
 * Single source of truth. All app state lives here; modules subscribe to changes.
 */

const initialState = {
  positions: [],
  selected_contract: null,
};

let state = { ...initialState };
const listeners = new Set();

export function getState() {
  return state;
}

export function setState(partial) {
  if (!partial || typeof partial !== 'object') return;
  state = { ...state, ...partial };
  listeners.forEach((fn) => fn(state));
}

export function subscribe(fn) {
  if (typeof fn === 'function') listeners.add(fn);
  return () => listeners.delete(fn);
}

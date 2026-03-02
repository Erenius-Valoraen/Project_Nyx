/**
 * Transport abstraction
 * - HTTP: fetch (existing API stays unchanged)
 * - WS: realtime push (state, positions, ticks)
 */

const BASE = '';

/* ──────────────────────────
   HTTP (unchanged)
────────────────────────── */

export async function request(path, options = {}) {
  const url = path.startsWith('http') ? path : BASE + path;
  const res = await fetch(url, options);
  const text = await res.text();
  let data;
  try {
    data = JSON.parse(text);
  } catch {
    data = text;
  }
  return { ok: res.ok, status: res.status, data };
}

export function get(path) {
  return request(path, { method: 'GET' });
}

export function post(path, body) {
  return request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
}

/* ──────────────────────────
   WebSocket
────────────────────────── */

let ws = null;
let wsConnected = false;
let reconnectTimer = null;

const listeners = new Map();

const WS_URL =
  (location.protocol === 'https:' ? 'wss://' : 'ws://') +
  location.host +
  '/ws';

export function connectWS() {
  if (wsConnected || ws) return;

  ws = new WebSocket(WS_URL);

  ws.onopen = () => {
    wsConnected = true;
    console.log('[WS] connected');
  };

  ws.onmessage = (e) => {
    let msg;
    try {
      msg = JSON.parse(e.data);
    } catch {
      return;
    }

    const { type, payload } = msg;
    const subs = listeners.get(type);
    if (subs) subs.forEach((fn) => fn(payload));
  };

  ws.onclose = () => {
    console.warn('[WS] disconnected');
    wsConnected = false;
    ws = null;
    reconnectTimer = setTimeout(connectWS, 1000);
  };

  ws.onerror = () => {
    ws?.close();
  };
}

export function subscribe(type, fn) {
  if (!listeners.has(type)) listeners.set(type, new Set());
  listeners.get(type).add(fn);
  return () => listeners.get(type)?.delete(fn);
}

export function sendWS(type, payload) {
  if (!wsConnected) return;
  ws.send(JSON.stringify({ type, payload }));
}
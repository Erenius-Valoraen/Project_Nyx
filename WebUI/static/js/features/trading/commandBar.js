/**
 * Command bar: buy/sell/use commands. Delegates to orders.
 */

import { placeOrder, switchContract } from './orders.js';

export function getContractsFromHint() {
  const hint = document.querySelector('.command-hint');
  if (!hint) return [];
  const text = (hint.textContent || '').trim();
  const match = text.match(/Available:\s*(.*)/i);
  if (!match) return [];
  return match[1].split(',').map((s) => s.trim()).filter(Boolean);
}

export function handleCommandBar(event) {
  if (event.key !== 'Enter') return;
  const input = event.target;
  const command = (input.value || '').trim();
  input.value = '';
  if (!command) return;

  const parts = command.split(/\s+/);
  if (parts.length !== 2) {
    alert('Usage:\n buy <qty>\n sell <qty>\n use <symbol|index>');
    return;
  }
  const cmd = parts[0].toLowerCase();
  const arg = parts[1];

  if (cmd === 'use') {
    const idx = parseInt(arg, 10);
    if (!isNaN(idx)) {
      const contracts = getContractsFromHint();
      const symbol = contracts[idx - 1];
      if (!symbol) {
        alert('Invalid contract index');
        return;
      }
      switchContract(symbol);
      return;
    }
    switchContract(arg);
    return;
  }

  if (cmd !== 'buy' && cmd !== 'sell') {
    alert("Invalid side. Use 'buy' or 'sell'");
    return;
  }
  const qty = parseInt(arg, 10);
  if (isNaN(qty) || qty <= 0) {
    alert('Invalid quantity');
    return;
  }
  placeOrder(cmd, qty);
}

export function init(commandInput) {
  if (commandInput) commandInput.addEventListener('keydown', handleCommandBar);
}

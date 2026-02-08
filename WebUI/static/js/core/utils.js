/**
 * Formatting and UI helpers. No API calls.
 */

export function formatNumber(num, decimals = 2) {
  if (num === null || num === undefined) return '-';
  return Number(num).toFixed(decimals);
}

export function formatPL(pl) {
  if (pl === null || pl === undefined) return '-';
  const val = Number(pl);
  const formatted = val.toLocaleString('en-US', { minimumFractionDigits: 2, maximumFractionDigits: 2 });
  return val >= 0 ? `+${formatted}` : formatted;
}

export function getSideClass(side) {
  if (side === 'buy') return 'side-buy';
  if (side === 'sell') return 'side-sell';
  return 'side-flat';
}

export function getPLClass(pl) {
  if (pl === null || pl === undefined) return '';
  return Number(pl) >= 0 ? 'pl-positive' : 'pl-negative';
}

export function showToast(message, type = 'info', duration = 3000) {
  let container = document.querySelector('.notification-container');
  if (!container) {
    container = document.createElement('div');
    container.className = 'notification-container';
    document.body.appendChild(container);
  }
  const toast = document.createElement('div');
  toast.className = `notification ${type}`;
  const time = new Date().toLocaleTimeString([], { hour12: false, hour: '2-digit', minute: '2-digit', second: '2-digit' });
  toast.innerHTML = `<span style="opacity: 0.5">[${time}]</span> &gt; ${message}`;
  container.appendChild(toast);
  requestAnimationFrame(() => toast.classList.add('show'));
  const removeToast = () => {
    toast.classList.remove('show');
    toast.addEventListener('transitionend', () => toast.remove());
  };
  const autoHide = setTimeout(removeToast, duration);
  toast.onclick = () => {
    clearTimeout(autoHide);
    removeToast();
  };
}

/**
 * View switching (trade / chart).
 */

export function switchView(viewName) {
  document.querySelectorAll('.view').forEach((v) => v.classList.remove('active'));
  const target = document.getElementById(`view-${viewName || 'trade'}`);
  if (target) target.classList.add('active');
}

export function init() {
  switchView('trade');
  const tradeViewBtn = document.getElementById('trade-view');
  const chartViewBtn = document.getElementById('chart-view');
  if (tradeViewBtn) tradeViewBtn.addEventListener('click', () => switchView('trade'));
  if (chartViewBtn) chartViewBtn.addEventListener('click', () => switchView('chart'));
}

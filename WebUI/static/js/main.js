/**
 * Single entry point. Only this file is included in main_terminal.html.
 */

import { start as startPoller } from './core/poller.js';
import { init as initUiSync } from './sync/uiSync.js';
import { init as initInputs } from './ui/inputs.js';
import { init as initOptionChain } from './features/optionChain/optionChain.js';
import { init as initChart } from './features/chart/chart.js';

function init() {
  initUiSync();
  initInputs();

  const contracts = typeof window !== 'undefined' && window.ALL_CONTRACTS ? window.ALL_CONTRACTS : [];
  initOptionChain(contracts);
  initChart();

  startPoller();
}

if (document.readyState === 'loading') {
  document.addEventListener('DOMContentLoaded', init);
} else {
  init();
}

/**
 * Option chain: expiry tabs, strike table, LTP polling. Reads contracts from init(contracts).
 */

import * as api from '../../core/api.js';
import { switchContract } from '../trading/orders.js';

const PRICE_REFRESH_MS = 10_000;
let optionChainData = {};
let currentExpiry = null;
let pricePoller = null;
let spotPrice = null;

function processContract(contract) {
  const regex = /^([A-Z]+)(\d{2}[A-Z]{3}\d{2})(\d+)(CE|PE)$/;
  const match = (contract || '').match(regex);
  return match ? [match[0], match[1], match[2], match[3], match[4]] : null;
}

function getContractsForExpiry(chain, expiry) {
  const d = chain[expiry];
  return [...Object.values(d.ce), ...Object.values(d.pe)];
}

function renderExpiryTabs(data) {
  const container = document.querySelector('#expiry-tabs');
  if (!container) return;
  container.innerHTML = '';
  Object.keys(data).forEach((expiry, index) => {
    const tab = document.createElement('button');
    tab.className = `expiry-tab-btn ${index === 0 ? 'active' : ''}`;
    tab.innerText = expiry;
    tab.onclick = () => {
      document.querySelectorAll('.expiry-tab-btn').forEach((b) => b.classList.remove('active'));
      tab.classList.add('active');
      handleExpiryChange(data, expiry);
    };
    container.appendChild(tab);
  });
}

function renderTableForExpiry(data, expiry) {
  const tableBody = document.querySelector('#option-chain-body');
  if (!tableBody) return;
  tableBody.innerHTML = '';

  const expiryData = data[expiry];
  const allStrikes = [...new Set([...Object.keys(expiryData.ce), ...Object.keys(expiryData.pe)])]
    .map(Number)
    .sort((a, b) => a - b);

  const referencePrice = spotPrice > 0 ? spotPrice : allStrikes[Math.floor(allStrikes.length / 2)];
  const atmStrike = allStrikes.reduce(
    (prev, curr) => (Math.abs(curr - referencePrice) < Math.abs(prev - referencePrice) ? curr : prev)
  );

  allStrikes.forEach((strike) => {
    const isATM = strike === atmStrike;
    const ceSymbol = expiryData.ce[strike] || null;
    const peSymbol = expiryData.pe[strike] || null;

    const row = document.createElement('tr');
    if (isATM) {
      row.id = 'atm-row';
      row.classList.add('atm-highlight');
    }

    const ceCell = document.createElement('td');
    ceCell.className = 'ce-cell clickable-contract';
    ceCell.innerText = '-';
    if (ceSymbol) {
      ceCell.dataset.symbol = ceSymbol;
      ceCell.onclick = () => switchContract(ceSymbol);
    }

    const strikeCell = document.createElement('td');
    strikeCell.className = 'strike-cell';
    strikeCell.setAttribute('data-strike', strike);
    strikeCell.innerHTML = `<strong>${strike}</strong>`;

    const peCell = document.createElement('td');
    peCell.className = 'pe-cell clickable-contract';
    peCell.innerText = '-';
    if (peSymbol) {
      peCell.dataset.symbol = peSymbol;
      peCell.onclick = () => switchContract(peSymbol);
    }

    row.appendChild(ceCell);
    row.appendChild(strikeCell);
    row.appendChild(peCell);
    tableBody.appendChild(row);
  });

  setTimeout(() => {
    const atmRow = document.getElementById('atm-row');
    if (atmRow) atmRow.scrollIntoView({ behavior: 'smooth', block: 'center' });
  }, 150);
}

async function updateSpotPrice() {
  try {
    const data = await api.getNiftyLtp();
    const val = Number(data && data.response);
    if (!isNaN(val) && val > 0) spotPrice = val;
  } catch (e) {
    console.error('Spot fetch failed:', e);
  }
}

function updatePricesInTable(priceMap) {
  Object.keys(priceMap).forEach((symbol) => {
    document.querySelectorAll(`td[data-symbol="${symbol}"]`).forEach((cell) => {
      cell.innerText = priceMap[symbol];
    });
  });
}

function syncATMHighlight() {
  if (!spotPrice || spotPrice <= 0) return;
  const rows = Array.from(document.querySelectorAll('#option-chain-body tr'));
  let closestRow = null;
  let minDiff = Infinity;
  rows.forEach((row) => {
    const strikeCell = row.querySelector('.strike-cell');
    if (!strikeCell) return;
    const strike = Number(strikeCell.getAttribute('data-strike'));
    const diff = Math.abs(strike - spotPrice);
    if (diff < minDiff) {
      minDiff = diff;
      closestRow = row;
    }
    row.classList.remove('atm-highlight');
    row.removeAttribute('id');
  });
  if (closestRow) {
    closestRow.id = 'atm-row';
    closestRow.classList.add('atm-highlight');
  }
}

async function fetchPrices(contractList) {
  await updateSpotPrice();
  try {
    const result = await api.postOptLtp({ contracts: contractList });
    if (result && result.ok && result.data) {
      updatePricesInTable(result.data);
      syncATMHighlight();
    }
  } catch (err) {
    console.error('Price fetch failed:', err);
  }
}

function handleExpiryChange(chain, expiry) {
  currentExpiry = expiry;
  if (pricePoller) {
    clearInterval(pricePoller);
    pricePoller = null;
  }

  updateSpotPrice().then(() => {
    renderTableForExpiry(chain, expiry);
    const selectedContracts = getContractsForExpiry(chain, expiry);
    fetchPrices(selectedContracts);
    pricePoller = setInterval(() => fetchPrices(selectedContracts), PRICE_REFRESH_MS);
  });
}

export function init(contracts = []) {
  optionChainData = {};
  contracts.forEach((rawContract) => {
    const processed = processContract(rawContract);
    if (!processed) return;
    const [, , expiry, strikeStr, type] = processed;
    const typeKey = type.toLowerCase();
    const strike = parseInt(strikeStr, 10);
    if (!optionChainData[expiry]) optionChainData[expiry] = { ce: {}, pe: {} };
    optionChainData[expiry][typeKey][strike] = rawContract;
  });

  renderExpiryTabs(optionChainData);
  const firstExpiry = Object.keys(optionChainData)[0];
  if (firstExpiry) handleExpiryChange(optionChainData, firstExpiry);
}

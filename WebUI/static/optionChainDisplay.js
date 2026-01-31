// ================== GLOBAL STATE ==================
let currentExpiry = null;
let pricePoller = null;
let spotPrice = null; 
const PRICE_REFRESH_MS = 10_000; 

// ================== INIT ==================
document.addEventListener("DOMContentLoaded", () => {
    let contracts = window.ALL_CONTRACTS || [];
    window.option_chain = {};

    contracts.forEach(rawContract => {
        let processed = processContract(rawContract);
        if (!processed) return;

        let [, instrument, expiry, strike, type] = processed;
        type = type.toLowerCase();
        strike = parseInt(strike);

        if (!option_chain[expiry]) {
            option_chain[expiry] = { ce: {}, pe: {} };
        }
        option_chain[expiry][type][strike] = rawContract;
    });

    renderExpiryTabs(option_chain);

    const firstExpiry = Object.keys(option_chain)[0];
    if (firstExpiry) {
        handleExpiryChange(option_chain, firstExpiry);
    }
});

// ================== CORE FLOW ==================
async function handleExpiryChange(option_chain, expiry) {
    currentExpiry = expiry;

    if (pricePoller) {
        clearInterval(pricePoller);
        pricePoller = null;
    }

    // Ensure we have spot price before the very first table render
    await updateSpotPrice();
    
    renderTableForExpiry(option_chain, expiry);

    const selectedContracts = getContractsForExpiry(option_chain, expiry);
    
    // Initial fetch immediately
    fetchPrices(selectedContracts);

    // Set up interval
    pricePoller = setInterval(() => {
        fetchPrices(selectedContracts);
    }, PRICE_REFRESH_MS);
}

// Added back the missing helper
function getContractsForExpiry(option_chain, expiry) {
    const expiryData = option_chain[expiry];
    const ceContracts = Object.values(expiryData.ce);
    const peContracts = Object.values(expiryData.pe);
    return [...ceContracts, ...peContracts];
}

// ================== TABLE RENDER ==================
function renderTableForExpiry(data, expiry) {
    const tableBody = document.querySelector("#option-chain-body");
    if (!tableBody) return;
    tableBody.innerHTML = "";

    const expiryData = data[expiry];

    let allStrikes = [...new Set([
        ...Object.keys(expiryData.ce),
        ...Object.keys(expiryData.pe)
    ])]
    .map(Number)
    .sort((a, b) => a - b);

    // Fallback logic if spotPrice is unavailable
    const referencePrice = (spotPrice && spotPrice > 0) ? spotPrice : allStrikes[Math.floor(allStrikes.length / 2)];

    const atmStrike = allStrikes.reduce((prev, curr) => {
        return Math.abs(curr - referencePrice) < Math.abs(prev - referencePrice) ? curr : prev;
    });

    allStrikes.forEach(strike => {
        const isATM = strike === atmStrike;
        const ceSymbol = expiryData.ce[strike] || null;
        const peSymbol = expiryData.pe[strike] || null;

        const row = document.createElement("tr");
        if (isATM) {
            row.id = "atm-row";
            row.classList.add("atm-highlight");
        }

        const ceCell = document.createElement("td");
        ceCell.className = "ce-cell clickable-contract";
        ceCell.innerText = "-";
        if (ceSymbol) {
            ceCell.dataset.symbol = ceSymbol;
            ceCell.onclick = () => switchContract(ceSymbol);
        }

        const strikeCell = document.createElement("td");
        strikeCell.className = "strike-cell";
        strikeCell.setAttribute("data-strike", strike);
        strikeCell.innerHTML = `<strong>${strike}</strong>`;

        const peCell = document.createElement("td");
        peCell.className = "pe-cell clickable-contract";
        peCell.innerText = "-";
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
        const atmRow = document.getElementById("atm-row");
        if (atmRow) {
            atmRow.scrollIntoView({ behavior: "smooth", block: "center" });
        }
    }, 150);
}

// ================== PRICE FETCHING & UPDATES ==================
async function updateSpotPrice() {
    try {
        const resp = await fetch('/api/nifty_ltp');
        const data = await resp.json();
        const val = Number(data['response']);
        if (!isNaN(val) && val > 0) {
            spotPrice = val;
        }
    } catch (e) {
        console.error("Spot fetch failed:", e);
    }
}

async function fetchPrices(contractList) {
    try {
        await updateSpotPrice();

        const response = await fetch("/api/opt_ltp", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ contracts: contractList }),
        });

        const result = await response.json();
        if (result.ok && result.data) {
            updatePricesInTable(result.data);
            syncATMHighlight(); 
        }
    } catch (error) {
        console.error("Price fetch failed:", error);
    }
}

function updatePricesInTable(priceMap) {
    Object.keys(priceMap).forEach(symbol => {
        const cells = document.querySelectorAll(`td[data-symbol="${symbol}"]`);
        cells.forEach(cell => { cell.innerText = priceMap[symbol]; });
    });
}

function syncATMHighlight() {
    if (!spotPrice || spotPrice <= 0) return;

    const rows = Array.from(document.querySelectorAll("#option-chain-body tr"));
    if (rows.length === 0) return;

    let closestRow = null;
    let minDiff = Infinity;

    rows.forEach(row => {
        const strikeCell = row.querySelector(".strike-cell");
        if (!strikeCell) return;
        
        const strike = Number(strikeCell.getAttribute("data-strike"));
        const diff = Math.abs(strike - spotPrice);

        if (diff < minDiff) {
            minDiff = diff;
            closestRow = row;
        }
        row.classList.remove("atm-highlight");
        row.removeAttribute("id");
    });

    if (closestRow) {
        closestRow.id = "atm-row";
        closestRow.classList.add("atm-highlight");
    }
}

// ================== UTILS ==================
function processContract(contract) {
    const regex = /^([A-Z]+)(\d{2}[A-Z]{3}\d{2})(\d+)(CE|PE)$/;
    const match = contract.match(regex);
    return match ? [match[0], match[1], match[2], match[3], match[4]] : null;
}

function renderExpiryTabs(data) {
    const tabsContainer = document.querySelector("#expiry-tabs");
    if (!tabsContainer) return;
    tabsContainer.innerHTML = "";
    Object.keys(data).forEach((expiry, index) => {
        const tab = document.createElement("button");
        tab.className = `expiry-tab-btn ${index === 0 ? 'active' : ''}`;
        tab.innerText = expiry;
        tab.onclick = () => {
            document.querySelectorAll(".expiry-tab-btn").forEach(b => b.classList.remove("active"));
            tab.classList.add("active");
            handleExpiryChange(data, expiry);
        };
        tabsContainer.appendChild(tab);
    });
}
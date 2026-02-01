/* ============================================
   MANEUVER OPTIMIZATION LOGIC (CLASSIC RESTORED)
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
    initOptimization();
});

function initOptimization() {
    console.log("Initializing Optimization (Classic v2)");
    // Initialize algorithm selection
    setupAlgorithmSelection('standard');
    setupAlgorithmSelection('kessler');

    // Attach button listeners
    const btnStandard = document.getElementById('optimize-standard-btn');
    if (btnStandard) {
        btnStandard.addEventListener('click', () => runOptimization('standard'));
    }

    const btnKessler = document.getElementById('optimize-kessler-btn');
    if (btnKessler) {
        btnKessler.addEventListener('click', () => runOptimization('kessler'));
    }
}

/* ========== ALGORITHM SELECTION ========== */

function setupAlgorithmSelection(mode) {
    const grid = document.getElementById(`algo-grid-${mode}`);
    if (!grid) return;

    const cards = grid.querySelectorAll('.agent-card');

    cards.forEach(card => {
        card.addEventListener('click', () => {
            // Deselect others
            cards.forEach(c => c.classList.remove('selected'));
            // Select clicked
            card.classList.add('selected');
        });
    });
}

function getSelectedAlgorithm(mode) {
    const grid = document.getElementById(`algo-grid-${mode}`);
    const selected = grid.querySelector('.agent-card.selected');
    return selected ? selected.dataset.agent : 'cross_entropy';
}

/* ========== RUN OPTIMIZATION ========== */

// Ensure global scope access
window.runOptimization = runOptimization;

async function runOptimization(mode) {
    console.log(`Running optimization for mode: ${mode}`);

    const btn = document.getElementById(`optimize-${mode}-btn`);
    const resultsSection = document.getElementById(`result-${mode}`); // Singular 'result' as per restored HTML

    if (!btn) {
        console.error(`Run button not found: optimize-${mode}-btn`);
        alert(`Internal Error: Run button optimize-${mode}-btn missing`);
        return;
    }

    if (!resultsSection) {
        console.error(`Results section not found: result-${mode}`);
        alert(`Internal Error: Result section result-${mode} missing`);
        return;
    }

    // Get inputs
    const iterInput = document.getElementById(`iter-${mode}`);
    const maneuversInput = document.getElementById(`maneuvers-${mode}`);

    const iterations = parseInt(iterInput.value);
    const nManeuvers = parseInt(maneuversInput.value);
    const algorithm = getSelectedAlgorithm(mode);

    // Get TLEs (assumed to be in other tab or hidden inputs)
    // Note: The original index.html relied on global variables or inputs in other tabs.
    // We check the inputs in the conjunction/home tab if they exist.
    const satelliteTle = document.getElementById('satellite-tle')?.value;
    const debrisTles = document.getElementById('debris-tles')?.value;

    if (!satelliteTle || !debrisTles) {
        alert("Please load Satellite and Debris TLEs in the Conjunction Screening tab first or load sample data.");
        return;
    }

    // Set Loading State
    const originalText = btn.querySelector('.btn-text').textContent;
    btn.disabled = true;
    btn.querySelector('.btn-text').textContent = "Optimizing...";

    // Hide previous results
    resultsSection.style.display = 'none';

    try {
        const response = await fetch('/optimize-maneuver', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                satellite_tle: satelliteTle,
                debris_tles: debrisTles,
                agent: algorithm,
                n_iterations: iterations,
                n_maneuvers: nManeuvers,
                mode: mode
            })
        });

        const result = await response.json();

        if (result.success && result.data) {
            displayOptimizationResults(mode, result.data, algorithm, iterations, nManeuvers);
        } else {
            alert(`Optimization failed: ${result.error || 'Unknown error'}`);
        }

    } catch (error) {
        console.error("Optimization error:", error);
        alert(`Connection error: ${error.message}`);
    } finally {
        btn.disabled = false;
        btn.querySelector('.btn-text').textContent = originalText;
    }
}

function displayOptimizationResults(mode, data, algorithm, iterations, nManeuvers) {
    const resultsSection = document.getElementById(`result-${mode}`);

    // Update Meta
    const agentDisplay = document.getElementById(`result-agent-${mode}`);
    if (agentDisplay) {
        agentDisplay.textContent = `${formatAlgoName(algorithm)} (Iter: ${iterations}, Mnv: ${nManeuvers})`;
    }

    // Update Metrics
    const fuelDisplay = document.getElementById(`fuel-${mode}`);
    if (fuelDisplay) fuelDisplay.textContent = (data.total_fuel_consumption || 0).toFixed(3);

    const probDisplay = document.getElementById(`prob-${mode}`);
    if (probDisplay) probDisplay.textContent = (data.collision_probability || 0).toExponential(2);

    // Populate Table
    const tbody = document.getElementById(`maneuver-tbody-${mode}`);
    if (tbody) {
        tbody.innerHTML = '';

        if (data.maneuvers && data.maneuvers.length > 0) {
            data.maneuvers.forEach((mnv, index) => {
                const row = document.createElement('tr');

                const dv = mnv.dv || [0, 0, 0];
                const totalDv = Math.sqrt(dv[0] ** 2 + dv[1] ** 2 + dv[2] ** 2);

                row.innerHTML = `
                    <td>${mnv.time ? mnv.time.toFixed(4) : `T+${index * 100}s`}</td>
                    <td>${dv[0].toFixed(4)}</td>
                    <td>${dv[1].toFixed(4)}</td>
                    <td>${dv[2].toFixed(4)}</td>
                    <td>${totalDv.toFixed(4)}</td>
                `;
                tbody.appendChild(row);
            });
        } else {
            tbody.innerHTML = `<tr><td colspan="5" style="text-align:center;">No maneuvers required (Safe)</td></tr>`;
        }
    }

    // Show Section
    resultsSection.style.display = 'block';
}

function formatAlgoName(snakeCase) {
    return snakeCase.split('_').map(word => word.charAt(0).toUpperCase() + word.slice(1)).join(' ');
}

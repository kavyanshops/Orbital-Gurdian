/**
 * Collision Avoidance Alert System - Frontend Application
 * Space Hackathon 2026
 * 
 * Handles API communication, UI updates, and user interactions.
 */

// Configuration
const CONFIG = {
    API_BASE_URL: 'http://localhost:5050',
    ENDPOINTS: {
        ANALYZE: '/analyze',
        HEALTH: '/health',
        SAMPLE_DATA: '/sample-data',
        ORBITS: '/orbits',
        OPTIMIZE: '/optimize-maneuver',
        DETECT: '/detect-debris',
        DETECTION_SAMPLE: '/detection-sample'
    }
};

// Sample TLE data (real ISS and debris TLEs)
const SAMPLE_DATA = {
    satellite: `ISS (ZARYA)
1 25544U 98067A   24001.50000000  .00016717  00000-0  10270-3 0  9002
2 25544  51.6400 208.9163 0006703  40.5765 319.5509 15.49560722999999`,

    debris: `FENGYUN 1C DEB
1 29479U 99025AHK 24001.50000000  .00002000  00000-0  10000-3 0  9999
2 29479  98.5000 100.0000 0010000 200.0000 160.0000 14.30000000999999
FENGYUN 1C DEB
1 30023U 99025BQC 24001.50000000  .00001500  00000-0  80000-4 0  9999
2 30023  99.0000 150.0000 0020000 180.0000 180.0000 14.20000000999999
FENGYUN 1C DEB
1 31135U 99025DKP 24001.50000000  .00001800  00000-0  90000-4 0  9999
2 31135  97.8000 120.0000 0015000 220.0000 140.0000 14.35000000999999
COSMOS 2251 DEB
1 34427U 93036AAA 24001.50000000  .00001200  00000-0  70000-4 0  9999
2 34427  74.0000  80.0000 0025000 150.0000 210.0000 14.40000000999999
IRIDIUM 33 DEB
1 33775U 97051AAA 24001.50000000  .00001000  00000-0  60000-4 0  9999
2 33775  86.4000 200.0000 0018000 100.0000 260.0000 14.45000000999999`
};

// DOM Elements
const elements = {
    // Inputs
    satelliteTle: document.getElementById('satellite-tle'),
    debrisTles: document.getElementById('debris-tles'),
    duration: document.getElementById('duration'),
    timestep: document.getElementById('timestep'),
    usePrefilter: document.getElementById('use-prefilter'),

    // Buttons
    analyzeBtn: document.getElementById('analyze-btn'),
    loadSampleSatellite: document.getElementById('load-sample-satellite'),
    loadSampleDebris: document.getElementById('load-sample-debris'),

    // Status
    connectionStatus: document.getElementById('connection-status'),

    // Results
    resultsSection: document.getElementById('results-section'),
    statusBanner: document.getElementById('status-banner'),
    statusIcon: document.getElementById('status-icon'),
    statusTitle: document.getElementById('status-title'),
    statusSubtitle: document.getElementById('status-subtitle'),

    // Summary
    summarySatellite: document.getElementById('summary-satellite'),
    summaryDebrisCount: document.getElementById('summary-debris-count'),
    summaryWarnings: document.getElementById('summary-warnings'),
    summaryClosest: document.getElementById('summary-closest'),

    // Table
    resultsTbody: document.getElementById('results-tbody'),
    resultsInfo: document.getElementById('results-info'),

    // Metadata
    metadataGrid: document.getElementById('metadata-grid'),

    // Loading
    loadingOverlay: document.getElementById('loading-overlay'),
    loadingText: document.getElementById('loading-text'),
    loadingSubtext: document.getElementById('loading-subtext'),

    errorModal: document.getElementById('error-modal'),
    errorMessage: document.getElementById('error-message'),
    modalClose: document.getElementById('modal-close'),
    errorCloseBtn: document.getElementById('error-close-btn'),

    // Optimization - Standard
    iterStandard: document.getElementById('iter-standard'),
    countStandard: document.getElementById('count-standard'),
    optimizeStandardBtn: document.getElementById('optimize-standard-btn'),
    resultStandard: document.getElementById('result-standard'),
    fuelStandard: document.getElementById('fuel-standard'),
    probStandard: document.getElementById('prob-standard'),
    maneuverTbodyStandard: document.getElementById('maneuver-tbody-standard'),

    // Optimization - Kessler
    iterKessler: document.getElementById('iter-kessler'),
    countKessler: document.getElementById('count-kessler'),
    optimizeKesslerBtn: document.getElementById('optimize-kessler-btn'),
    resultKessler: document.getElementById('result-kessler'),
    fuelKessler: document.getElementById('fuel-kessler'),
    probKessler: document.getElementById('prob-kessler'),
    maneuverTbodyKessler: document.getElementById('maneuver-tbody-kessler'),

    // Detection
    debrisImageInput: document.getElementById('debris-image-input'),
    detectBtn: document.getElementById('detect-btn'),
    uploadArea: document.getElementById('upload-area'),
    imagePreview: document.getElementById('image-preview'),
    previewImg: document.getElementById('preview-img'),
    removeImageBtn: document.getElementById('remove-image'),
    loadSampleImageBtn: document.getElementById('load-sample-image'),
    detectionResults: document.getElementById('detection-results'),
    resultImg: document.getElementById('result-img'),
    detCount: document.getElementById('det-count'),
    detConf: document.getElementById('det-conf')
};

// State
let isAnalyzing = false;
let orbitViewer = null;

/**
 * Initialize the application
 */
function init() {
    // Set up event listeners
    elements.analyzeBtn.addEventListener('click', runAnalysis);
    elements.analyzeBtn.addEventListener('click', runAnalysis);
    // elements.optimizeBtn.addEventListener('click', optimizeManeuvers); // Removed old button
    elements.loadSampleSatellite.addEventListener('click', loadSampleSatellite);
    elements.loadSampleDebris.addEventListener('click', loadSampleDebris);

    // Detection events
    elements.detectBtn.addEventListener('click', detectDebris);
    elements.loadSampleImageBtn.addEventListener('click', loadSampleImage);
    elements.removeImageBtn.addEventListener('click', clearImage);
    elements.uploadArea.addEventListener('click', (e) => {
        if (e.target !== elements.removeImageBtn) elements.debrisImageInput.click();
    });
    elements.debrisImageInput.addEventListener('change', handleImageUpload);

    elements.modalClose.addEventListener('click', hideErrorModal);
    elements.errorCloseBtn.addEventListener('click', hideErrorModal);

    // Optimization buttons
    if (elements.optimizeStandardBtn) {
        elements.optimizeStandardBtn.addEventListener('click', () => runOptimization('standard'));
    }
    if (elements.optimizeKesslerBtn) {
        elements.optimizeKesslerBtn.addEventListener('click', () => runOptimization('kessler'));
    }

    // Agent card selection
    document.querySelectorAll('.agent-card').forEach(card => {
        card.addEventListener('click', function () {
            const mode = this.dataset.mode;
            // Deselect others in same section
            document.querySelectorAll(`.agent-card[data-mode="${mode}"]`).forEach(c => c.classList.remove('selected'));
            this.classList.add('selected');
        });
    });

    // Tab switching
    document.querySelectorAll('.nav-tab').forEach(tab => {
        tab.addEventListener('click', () => {
            // Update active tab
            document.querySelectorAll('.nav-tab').forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Switch views
            const viewId = tab.dataset.tab;
            document.querySelectorAll('.view-section').forEach(view => {
                view.style.display = view.id === viewId ? 'block' : 'none';
            });

            // Handle Shared Inputs visibility
            const sharedInputs = document.getElementById('shared-orbital-inputs');
            if (sharedInputs) {
                if (viewId === 'view-analysis' || viewId === 'view-optimization') {
                    sharedInputs.style.display = 'block';
                } else {
                    sharedInputs.style.display = 'none';
                }
            }
        });
    });



    // 3D viewer toggle
    const toggle3dBtn = document.getElementById('toggle-3d');
    if (toggle3dBtn) {
        toggle3dBtn.addEventListener('click', () => {
            const viewer = document.getElementById('orbit-viewer');
            if (viewer) {
                viewer.style.display = viewer.style.display === 'none' ? 'block' : 'none';
            }
        });
    }

    // Check backend health
    checkHealth();

    // Load sample data on start for easy testing
    loadSampleSatellite();
    loadSampleDebris();
}

/**
 * Check backend health status
 */
async function checkHealth() {
    const statusDot = elements.connectionStatus.querySelector('.status-dot');
    const statusText = elements.connectionStatus.querySelector('.status-text');

    try {
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.HEALTH}`);
        if (response.ok) {
            statusDot.classList.add('connected');
            statusDot.classList.remove('error');
            statusText.textContent = 'Backend Connected';
        } else {
            throw new Error('Health check failed');
        }
    } catch (error) {
        statusDot.classList.add('error');
        statusDot.classList.remove('connected');
        statusText.textContent = 'Backend Offline';
    }
}

/**
 * Load sample satellite TLE
 */
function loadSampleSatellite() {
    elements.satelliteTle.value = SAMPLE_DATA.satellite;
    elements.satelliteTle.dispatchEvent(new Event('input'));
}

/**
 * Load sample debris TLEs
 */
function loadSampleDebris() {
    elements.debrisTles.value = SAMPLE_DATA.debris;
    elements.debrisTles.dispatchEvent(new Event('input'));
}

/**
 * Show loading overlay
 */
function showLoading(text = 'Propagating orbits...', subtext = '') {
    elements.loadingText.textContent = text;
    elements.loadingSubtext.textContent = subtext;
    elements.loadingOverlay.classList.add('active');
}

/**
 * Hide loading overlay
 */
function hideLoading() {
    elements.loadingOverlay.classList.remove('active');
}

/**
 * Show error modal
 */
function showErrorModal(message) {
    elements.errorMessage.textContent = message;
    elements.errorModal.style.display = 'flex';
}

/**
 * Hide error modal
 */
function hideErrorModal() {
    elements.errorModal.style.display = 'none';
}

/**
 * Validate input data
 */
function validateInput() {
    const satelliteTle = elements.satelliteTle.value.trim();
    const debrisTles = elements.debrisTles.value.trim();

    if (!satelliteTle) {
        throw new Error('Please enter a satellite TLE');
    }

    const satLines = satelliteTle.split('\n').filter(line => line.trim());
    if (satLines.length < 3) {
        throw new Error('Satellite TLE must have 3 lines (name, line1, line2)');
    }

    if (!debrisTles) {
        throw new Error('Please enter at least one debris TLE');
    }

    const debrisLines = debrisTles.split('\n').filter(line => line.trim());
    if (debrisLines.length < 3 || debrisLines.length % 3 !== 0) {
        throw new Error('Debris TLEs must have lines in groups of 3 (name, line1, line2)');
    }

    return {
        satellite_tle: satelliteTle,
        debris_tles: debrisTles,
        duration_hours: parseFloat(elements.duration.value),
        time_step_seconds: parseFloat(elements.timestep.value),
        use_prefilter: elements.usePrefilter.checked
    };
}

/**
 * Run conjunction analysis
 */
async function runAnalysis() {
    if (isAnalyzing) return;

    try {
        isAnalyzing = true;
        elements.analyzeBtn.disabled = true;

        // Validate input
        const requestData = validateInput();

        // Calculate expected steps  
        const steps = Math.ceil((requestData.duration_hours * 3600) / requestData.time_step_seconds);
        const debrisCount = requestData.debris_tles.split('\n').filter(l => l.trim()).length / 3;

        showLoading(
            'Propagating orbits...',
            `Calculating ${steps.toLocaleString()} timesteps for ${debrisCount} debris objects`
        );

        // Make API request
        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.ANALYZE}`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();

        if (!result.success) {
            throw new Error(result.error || 'Analysis failed');
        }

        // Display results
        displayResults(result.data);

    } catch (error) {
        console.error('Analysis error:', error);
        showErrorModal(error.message);
    } finally {
        isAnalyzing = false;
        elements.analyzeBtn.disabled = false;
        hideLoading();
    }
}

/**
 * Display analysis results
 */
function displayResults(data) {
    // Show results section
    elements.resultsSection.style.display = 'block';

    // Update status banner
    const hasWarnings = data.overall_status === 'WARNINGS_PRESENT';
    elements.statusBanner.classList.toggle('warning', hasWarnings);
    elements.statusIcon.textContent = hasWarnings ? '⚠️' : '✓';
    elements.statusTitle.textContent = hasWarnings ? 'Warnings Detected!' : 'All Clear';
    elements.statusSubtitle.textContent = hasWarnings
        ? `${data.warnings_count} debris object(s) within 10 km threshold`
        : 'No debris objects within alert threshold';

    // Update summary cards
    elements.summarySatellite.textContent = data.satellite_name;
    elements.summaryDebrisCount.textContent = data.debris_analyzed;
    elements.summaryWarnings.textContent = data.warnings_count;

    // Find closest approach
    const analyzedResults = data.results.filter(r => r.status !== 'FILTERED');
    if (analyzedResults.length > 0) {
        const closest = analyzedResults[0];
        elements.summaryClosest.textContent = `${closest.min_distance_km.toFixed(3)} km`;
    } else {
        elements.summaryClosest.textContent = '-';
    }

    // Update results table
    elements.resultsTbody.innerHTML = '';
    elements.resultsInfo.textContent = `${data.results.length} objects • Sorted by closest approach`;

    data.results.forEach(result => {
        const row = document.createElement('tr');

        // Status badge
        const statusClass = result.status.toLowerCase();
        const statusEmoji = result.status === 'WARNING' ? '🚨' : (result.status === 'SAFE' ? '✅' : '⏭️');

        // Distance formatting
        let distanceHtml = '-';
        if (result.min_distance_km !== null) {
            const isClose = result.min_distance_km < 10;
            distanceHtml = `<span class="distance-value ${isClose ? 'critical' : ''}">${result.min_distance_km.toFixed(3)} km</span>`;
        }

        // Time formatting
        let timeHtml = '-';
        if (result.closest_approach_time) {
            const date = parseTimestamp(result.closest_approach_time);
            timeHtml = `<span class="time-value">${formatDateTime(date)}</span>`;
        } else if (result.reason) {
            timeHtml = `<span class="time-value">${result.reason}</span>`;
        }

        // Maneuver recommendation formatting
        let maneuverHtml = '-';
        if (result.maneuver_recommendation) {
            const rec = result.maneuver_recommendation;
            const urgencyClass = (rec.urgency || 'unknown').toLowerCase();
            maneuverHtml = `
                <div class="maneuver-rec ${urgencyClass}">
                    <span class="maneuver-urgency ${urgencyClass}">${rec.urgency}</span>
                    <div class="maneuver-action">${rec.action}</div>
                    <div class="maneuver-details">
                        <strong>TCA:</strong> ${rec.hours_to_tca}h • 
                        <strong>ΔV:</strong> ~${rec.estimated_delta_v_ms} m/s
                    </div>
                </div>
            `;
        }

        row.innerHTML = `
            <td><span class="status-badge ${statusClass}">${statusEmoji} ${result.status}</span></td>
            <td>${escapeHtml(result.debris_id)}</td>
            <td>${distanceHtml}</td>
            <td>${timeHtml}</td>
            <td>${maneuverHtml}</td>
        `;

        elements.resultsTbody.appendChild(row);
    });

    // Update metadata
    elements.metadataGrid.innerHTML = `
        <div class="metadata-item">
            <span class="metadata-label">Analysis Start</span>
            <span class="metadata-value">${formatDateTime(parseTimestamp(data.analysis_start))}</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Analysis End</span>
            <span class="metadata-value">${formatDateTime(parseTimestamp(data.analysis_end))}</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Time Step</span>
            <span class="metadata-value">${data.time_step_seconds}s</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Pre-filtered</span>
            <span class="metadata-value">${data.debris_filtered} objects</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Alert Threshold</span>
            <span class="metadata-value">10 km</span>
        </div>
        <div class="metadata-item">
            <span class="metadata-label">Satellite Catalog #</span>
            <span class="metadata-value">${data.satellite_catalog_number}</span>
        </div>
    `;

    // Scroll to results
    elements.resultsSection.scrollIntoView({ behavior: 'smooth' });

    // Initialize and show 3D orbit viewer
    const orbitCard = document.getElementById('orbit-card');
    if (orbitCard && window.OrbitViewer) {
        orbitCard.style.display = 'block';
        initOrbitViewer(data);
    }

    // Note: optimization is now in a separate tab, so we don't auto-show it here.
}

/**
 * Initialize 3D orbit viewer with analysis data
 */
async function initOrbitViewer(analysisData) {
    try {
        if (!orbitViewer) {
            orbitViewer = new OrbitViewer('orbit-viewer');
            await orbitViewer.init();
        }

        // Fetch orbit trajectory data
        const requestData = {
            satellite_tle: elements.satelliteTle.value,
            debris_tles: elements.debrisTles.value,
            duration_hours: 2  // Short duration for visualization
        };

        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.ORBITS}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(requestData)
        });

        const result = await response.json();
        if (result.success && result.data) {
            // Mark warning debris
            const warningIds = new Set(
                analysisData.results
                    .filter(r => r.status === 'WARNING')
                    .map(r => r.debris_id)
            );

            result.data.debris = result.data.debris.map(d => ({
                ...d,
                isWarning: warningIds.has(d.name)
            }));

            orbitViewer.loadOrbitData(result.data);
        }
    } catch (error) {
        console.warn('3D viewer initialization failed:', error);
    }
}

/**
 * Format date/time for display
 */
function formatDateTime(date) {
    // Handle invalid dates gracefully
    if (isNaN(date.getTime())) {
        return 'Invalid time';
    }
    return date.toISOString().replace('T', ' ').substring(0, 19) + ' UTC';
}

/**
 * Parse timestamp string to Date, handling malformed ISO strings
 */
function parseTimestamp(timestamp) {
    if (!timestamp) return null;
    // Handle timestamps with double timezone indicators like "+00:00Z"
    const cleaned = timestamp.replace(/\+00:00Z$/, 'Z').replace(/Z+$/, 'Z');
    return new Date(cleaned);
}

/**
 * Escape HTML to prevent XSS
 */
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}



/**
 * Handle image upload for detection
 */
function handleImageUpload(event) {
    const file = event.target.files[0];
    if (!file) return;

    // Validate file type
    if (!file.type.startsWith('image/')) {
        showErrorModal('Please upload an image file (PNG, JPG).');
        return;
    }

    const reader = new FileReader();
    reader.onload = (e) => {
        elements.previewImg.src = e.target.result;
        elements.imagePreview.style.display = 'block';
        elements.detectBtn.disabled = false;

        // Hide previous results
        elements.detectionResults.style.display = 'none';
        document.querySelector('.upload-placeholder').style.display = 'none';
    };
    reader.readAsDataURL(file);
}

/**
 * Clear uploaded image
 */
function clearImage(e) {
    if (e) e.stopPropagation();
    elements.debrisImageInput.value = '';
    elements.imagePreview.style.display = 'none';
    elements.detectBtn.disabled = true;
    elements.detectionResults.style.display = 'none';
    document.querySelector('.upload-placeholder').style.display = 'flex';
}

/**
 * Load sample detection image
 */
async function loadSampleImage() {
    try {
        elements.loadSampleImageBtn.disabled = true;
        elements.loadSampleImageBtn.innerHTML = '<span class="loading-spinner-small"></span> Loading...';

        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DETECTION_SAMPLE}`);
        const result = await response.json();

        if (!result.success) throw new Error(result.error);

        // Show original image as preview
        elements.previewImg.src = `data:image/png;base64,${result.data.original_image}`;
        elements.imagePreview.style.display = 'block';
        document.querySelector('.upload-placeholder').style.display = 'none';

        // Set up results
        elements.detectBtn.disabled = false;
        displayDetectionResults(result.data);

    } catch (error) {
        showErrorModal(error.message);
    } finally {
        elements.loadSampleImageBtn.disabled = false;
        elements.loadSampleImageBtn.innerHTML = '🎲 Load Sample';
    }
}

/**
 * Run debris detection
 */
async function detectDebris() {
    try {
        elements.detectBtn.disabled = true;
        elements.detectBtn.innerHTML = '<span class="loading-spinner-small"></span> Detecting...';

        // Convert image to base64
        const imgData = elements.previewImg.src;
        const modelType = document.getElementById('detection-model').value;

        const response = await fetch(`${CONFIG.API_BASE_URL}${CONFIG.ENDPOINTS.DETECT}`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                image_base64: imgData,
                model: modelType
            })
        });

        const result = await response.json();

        if (!result.success) throw new Error(result.error);

        displayDetectionResults(result.data);

    } catch (error) {
        showErrorModal(error.message);
    } finally {
        elements.detectBtn.disabled = false;
        elements.detectBtn.innerHTML = '<span class="btn-icon">👁️</span><span class="btn-text">Detect Debris</span>';
    }
}

/**
 * Display detection results
 */
function displayDetectionResults(data) {
    elements.resultImg.src = `data:image/png;base64,${data.visualization}`;
    elements.detCount.textContent = data.num_detections;

    // Calculate avg confidence
    if (data.detections.length > 0) {
        const avgConf = data.detections.reduce((sum, d) => sum + d.confidence, 0) / data.detections.length;
        elements.detConf.textContent = `${(avgConf * 100).toFixed(1)}%`;
    } else {
        elements.detConf.textContent = "-";
    }

    elements.detectionResults.style.display = 'block';

    // Scroll to results
    elements.detectionResults.scrollIntoView({ behavior: 'smooth' });
}



// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', init);

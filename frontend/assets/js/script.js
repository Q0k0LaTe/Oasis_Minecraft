// Configuration
const API_BASE_URL = 'http://localhost:3000/api/v2';
const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/v2\/?$/, '');
const POLL_INTERVAL = 2000;

// Global state
let currentJobId = null;
let pollInterval = null;

// DOM Elements
const generateBtn = document.getElementById('generateBtn');
const itemPromptInput = document.getElementById('itemPrompt');
const statusLog = document.getElementById('statusLog');
const statusBadge = document.getElementById('statusBadge');
const resultCard = document.getElementById('resultCard');
const emptyState = document.getElementById('emptyState');
const logStatusLabel = document.getElementById('logStatusLabel');

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('ModGen Studio AI initialized');
    if (itemPromptInput) {
        itemPromptInput.focus();
    }

    // Set up generate button
    if (generateBtn) {
        generateBtn.addEventListener('click', startGeneration);
    }
});

// Start mod generation
async function startGeneration() {
    const prompt = itemPromptInput ? itemPromptInput.value.trim() : '';

    if (!prompt || prompt.length < 5) {
        alert('Please describe your item in at least a few words.');
        return;
    }

    try {
        generateBtn.disabled = true;
        addLogEntry('Submitting request to AI...');
        updateStatusBadge('pending', 0);

        // Submit job
        const response = await fetch(`${API_BASE_URL}/generate`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ prompt })
        });

        if (!response.ok) {
            const errorData = await response.json().catch(() => ({}));
            throw new Error(errorData.detail || 'Failed to start generation');
        }

        const data = await response.json();
        currentJobId = data.jobId;

        addLogEntry(`Job started: ${currentJobId}`);
        updateStatusBadge('pending', 0);

        // Start polling
        startPolling();

    } catch (error) {
        console.error('Error starting generation:', error);
        addLogEntry(`Error: ${error.message}`, 'error');
        generateBtn.disabled = false;
        updateStatusBadge('failed', 0);
    }
}

// Polling system
function startPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
    }

    pollInterval = setInterval(async () => {
        if (!currentJobId) {
            stopPolling();
            return;
        }

        try {
            const response = await fetch(`${API_BASE_URL}/status/${currentJobId}`);
            if (!response.ok) {
                throw new Error('Failed to get job status');
            }

            const job = await response.json();
            handleJobStatus(job);

        } catch (error) {
            console.error('Polling error:', error);
            addLogEntry(`Polling error: ${error.message}`, 'error');
        }
    }, POLL_INTERVAL);
}

function stopPolling() {
    if (pollInterval) {
        clearInterval(pollInterval);
        pollInterval = null;
    }
}

// Handle different job statuses
function handleJobStatus(job) {
    const { status, logs, progress, result, error } = job;

    // Update logs
    if (logs && logs.length > 0) {
        updateLogs(logs);
    }

    // Update status badge
    updateStatusBadge(status, progress);

    // Handle different states
    switch (status) {
        case 'pending':
        case 'processing':
            // Continue polling
            break;

        case 'completed':
            stopPolling();
            showResult(result);
            break;

        case 'failed':
            stopPolling();
            showError(error);
            break;
    }
}

// Update status badge
function updateStatusBadge(status, progress) {
    if (!statusBadge) return;

    const statusText = {
        'pending': 'Pending',
        'processing': 'Processing',
        'completed': 'Complete',
        'failed': 'Failed'
    };

    statusBadge.textContent = statusText[status] || status;

    // Remove all status classes
    statusBadge.className = 'status-badge';

    if (status === 'completed') {
        statusBadge.classList.add('status-success');
    } else if (status === 'failed') {
        statusBadge.classList.add('status-error');
    } else {
        statusBadge.classList.add('status-working');
    }

    // Update log status label
    if (logStatusLabel) {
        logStatusLabel.textContent = statusText[status] || status;
    }
}

// Update logs
function updateLogs(logs) {
    if (!statusLog) return;

    statusLog.innerHTML = '';
    logs.slice(-15).forEach(log => {
        addLogEntry(log);
    });
}

function addLogEntry(text, type = 'info') {
    if (!statusLog) return;

    const entry = document.createElement('div');
    entry.className = 'status-log-entry';
    if (type === 'error') {
        entry.style.color = '#ff5555';
    }
    entry.innerHTML = `
        <span class="log-chevron">▸</span>
        <span class="log-text">${escapeHtml(text)}</span>
    `;
    statusLog.appendChild(entry);
    statusLog.scrollTop = statusLog.scrollHeight;
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Image selection modal logic removed - V2 API doesn't support image selection
// The V2 pipeline automatically generates and selects textures

// Show result
function showResult(result) {
    if (emptyState) emptyState.style.display = 'none';
    if (resultCard) resultCard.style.display = 'block';

    const resultName = document.getElementById('resultName');
    const resultId = document.getElementById('resultId');
    const resultTags = document.getElementById('resultTags');
    const resultIcon = document.getElementById('resultIcon');
    const resultCode = document.getElementById('resultCode');
    const detailSection = document.getElementById('detailSection');

    // V2 result format
    if (resultName) resultName.textContent = result.modName || 'Mod Generated';
    if (resultId) resultId.textContent = result.modId || 'N/A';

    // Tags - simplified for V2
    if (resultTags) {
        resultTags.innerHTML = `
            <span class="tag">V2 Pipeline</span>
            <span class="tag">Spec ${result.specVersion || '1.0'}</span>
        `;
    }

    // Icon placeholder - V2 doesn't return texture in result
    if (resultIcon) {
        resultIcon.innerHTML = `<div style="width: 100%; height: 100%; display: flex; align-items: center; justify-content: center; color: var(--mc-gray);">✓</div>`;
    }

    // Code section
    if (resultCode) {
        resultCode.textContent = `// ${result.modName || 'Mod'} generated successfully!\n// Download the .jar file to add to your Minecraft mods folder.`;
    }

    // Detail section
    if (detailSection) {
        detailSection.innerHTML = `
            <h3 style="color: var(--mc-yellow); margin-bottom: 15px;">📦 Mod Details</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Mod ID:</span>
                    <span class="detail-value">${result.modId || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Mod Name:</span>
                    <span class="detail-value">${result.modName || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">JAR File:</span>
                    <span class="detail-value">${result.jarFile || 'N/A'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Spec Version:</span>
                    <span class="detail-value">${result.specVersion || 'N/A'}</span>
                </div>
            </div>
            ${result.downloadUrl ? `
                <a href="${BACKEND_BASE_URL}${result.downloadUrl}" download="${result.jarFile || result.modId + '.jar'}" class="btn-download">
                    <span class="btn-icon">⬇</span> Download ${result.jarFile || 'mod.jar'}
                </a>
            ` : ''}
        `;
    }

    if (generateBtn) generateBtn.disabled = false;
    updateStatusBadge('completed', 100);
}

// Show error
function showError(error) {
    addLogEntry(`Error: ${error}`, 'error');
    updateStatusBadge('failed', 0);
    if (generateBtn) generateBtn.disabled = false;
    alert(`Generation failed: ${error}`);
}

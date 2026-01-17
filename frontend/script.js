// Configuration
const API_BASE_URL = 'http://localhost:3000/api';
const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');
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
        updateStatusBadge('queued', 0);

        // Submit job
        const response = await fetch(`${API_BASE_URL}/generate-mod`, {
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
        updateStatusBadge('queued', 0);

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
    const { status, logs, progress, pendingImageSelection, result, error } = job;

    // Update logs
    if (logs && logs.length > 0) {
        updateLogs(logs);
    }

    // Update status badge
    updateStatusBadge(status, progress);

    // Handle different states
    switch (status) {
        case 'queued':
        case 'analyzing':
        case 'generating':
        case 'generating_images':
            // Continue polling
            break;

        case 'awaiting_image_selection':
            stopPolling();
            showImageSelectionModal(pendingImageSelection);
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
        'queued': 'Queued',
        'analyzing': 'Analyzing',
        'generating': 'Generating',
        'generating_images': 'Creating Images',
        'awaiting_image_selection': 'Choose Textures',
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
    } else if (status === 'awaiting_image_selection') {
        statusBadge.classList.add('status-selection');
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

// Show image selection modal
function showImageSelectionModal(pendingImageSelection) {
    // Create modal
    const modal = document.createElement('div');
    modal.id = 'imageSelectionModal';
    modal.className = 'image-selection-modal';

    const assetTypes = Object.keys(pendingImageSelection);
    let currentAssetIndex = 0;
    let selections = {};

    function renderAssetSelection() {
        const assetType = assetTypes[currentAssetIndex];
        const assetData = pendingImageSelection[assetType];

        modal.innerHTML = `
            <div class="modal-content">
                <div class="modal-header">
                    <h2>Choose Texture (${currentAssetIndex + 1}/${assetTypes.length})</h2>
                    <p>${assetData.name} - ${assetType.toUpperCase()}</p>
                </div>
                <div class="image-grid">
                    ${assetData.options.map((img, index) => `
                        <div class="image-option" data-index="${index}">
                            <img src="data:image/png;base64,${img}" alt="Option ${index + 1}">
                            <div class="image-label">Option ${index + 1}</div>
                        </div>
                    `).join('')}
                </div>
                <div class="modal-actions">
                    <button class="btn-regenerate" id="regenerateBtn">
                        <span class="btn-icon">🔄</span> Regenerate 5 More
                    </button>
                    ${currentAssetIndex > 0 ? '<button class="btn-secondary" id="backBtn">← Back</button>' : ''}
                </div>
            </div>
        `;

        // Add click handlers for image selection
        modal.querySelectorAll('.image-option').forEach(option => {
            option.addEventListener('click', async () => {
                const selectedIndex = parseInt(option.dataset.index);
                selections[assetType] = selectedIndex;

                // Highlight selected option
                modal.querySelectorAll('.image-option').forEach(opt => {
                    opt.style.borderColor = 'transparent';
                });
                option.style.borderColor = '#ffff55';
                option.style.background = 'rgba(255, 255, 85, 0.2)';

                // Send selection to backend
                await selectImage(assetType, selectedIndex);

                // Small delay for visual feedback
                await new Promise(resolve => setTimeout(resolve, 300));

                // Move to next asset or close modal
                if (currentAssetIndex < assetTypes.length - 1) {
                    currentAssetIndex++;
                    renderAssetSelection();
                } else {
                    // All selections complete
                    document.body.removeChild(modal);
                    addLogEntry('All textures selected. Resuming generation...');
                    startPolling(); // Resume polling
                }
            });
        });

        // Regenerate button
        const regenerateBtn = modal.querySelector('#regenerateBtn');
        if (regenerateBtn) {
            regenerateBtn.addEventListener('click', async () => {
                regenerateBtn.disabled = true;
                regenerateBtn.innerHTML = '<span class="btn-icon">⏳</span> Generating...';

                try {
                    await regenerateImages(assetType);
                    // Re-fetch job status to get new images
                    const response = await fetch(`${API_BASE_URL}/status/${currentJobId}`);
                    const job = await response.json();
                    pendingImageSelection = job.pendingImageSelection;
                    renderAssetSelection();
                } catch (error) {
                    alert('Failed to regenerate images: ' + error.message);
                    regenerateBtn.disabled = false;
                    regenerateBtn.innerHTML = '<span class="btn-icon">🔄</span> Regenerate 5 More';
                }
            });
        }

        // Back button
        const backBtn = modal.querySelector('#backBtn');
        if (backBtn) {
            backBtn.addEventListener('click', () => {
                currentAssetIndex--;
                renderAssetSelection();
            });
        }
    }

    renderAssetSelection();
    document.body.appendChild(modal);
}

// Select image
async function selectImage(assetType, selectedIndex) {
    try {
        const response = await fetch(`${API_BASE_URL}/jobs/${currentJobId}/select-image`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ assetType, selectedIndex })
        });

        if (!response.ok) {
            throw new Error('Failed to select image');
        }

        addLogEntry(`Selected ${assetType} texture #${selectedIndex + 1}`);
    } catch (error) {
        console.error('Error selecting image:', error);
        throw error;
    }
}

// Regenerate images
async function regenerateImages(assetType) {
    try {
        const response = await fetch(`${API_BASE_URL}/jobs/${currentJobId}/regenerate-images`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ assetType })
        });

        if (!response.ok) {
            throw new Error('Failed to regenerate images');
        }

        addLogEntry(`Regenerated ${assetType} textures`);
    } catch (error) {
        console.error('Error regenerating images:', error);
        throw error;
    }
}

// Show result
function showResult(result) {
    if (emptyState) emptyState.style.display = 'none';
    if (resultCard) resultCard.style.display = 'block';

    const decisions = result.aiDecisions;

    const resultName = document.getElementById('resultName');
    const resultId = document.getElementById('resultId');
    const resultTags = document.getElementById('resultTags');
    const resultIcon = document.getElementById('resultIcon');
    const resultCode = document.getElementById('resultCode');
    const detailSection = document.getElementById('detailSection');

    if (resultName) resultName.textContent = decisions.itemName;
    if (resultId) resultId.textContent = `${decisions.modId}:${decisions.itemId}`;

    // Tags
    if (resultTags) {
        const tagsHtml = `
            <span class="tag rarity-${decisions.properties.rarity.toLowerCase()}">${decisions.properties.rarity}</span>
            <span class="tag">${decisions.properties.creativeTab.replace('_', ' ')}</span>
        `;
        resultTags.innerHTML = tagsHtml;
    }

    // Show texture
    if (result.textureBase64 && resultIcon) {
        resultIcon.innerHTML = `<img src="data:image/png;base64,${result.textureBase64}" alt="${decisions.itemName}" style="width: 100%; image-rendering: pixelated;">`;
    }

    // Code section
    if (resultCode) {
        resultCode.textContent = `// ${decisions.modName} generated successfully!\n// Download the .jar file to add to your Minecraft mods folder.`;
    }

    // Detail section
    if (detailSection) {
        detailSection.innerHTML = `
            <h3 style="color: var(--mc-yellow); margin-bottom: 15px;">📦 Mod Details</h3>
            <div class="detail-grid">
                <div class="detail-item">
                    <span class="detail-label">Mod ID:</span>
                    <span class="detail-value">${decisions.modId}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Author:</span>
                    <span class="detail-value">${decisions.author || 'AI Generator'}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Max Stack:</span>
                    <span class="detail-value">${decisions.properties.maxStackSize}</span>
                </div>
                <div class="detail-item">
                    <span class="detail-label">Fireproof:</span>
                    <span class="detail-value">${decisions.properties.fireproof ? 'Yes 🔥' : 'No'}</span>
                </div>
            </div>
            ${result.downloadUrl ? `
                <a href="${BACKEND_BASE_URL}${result.downloadUrl}" download="${decisions.modId}.jar" class="btn-download">
                    <span class="btn-icon">⬇</span> Download ${decisions.modName}.jar
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
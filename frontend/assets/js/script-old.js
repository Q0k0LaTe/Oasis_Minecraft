
// Configuration
const API_BASE_URL = 'http://localhost:3000/api'; // Change this to your backend URL
const BACKEND_BASE_URL = API_BASE_URL.replace(/\/api\/?$/, '');

// DOM Elements
const modForm = document.getElementById('modForm');
const generateBtn = document.getElementById('generateBtn');
const loadingOverlay = document.getElementById('loadingOverlay');
const loadingSubtext = document.getElementById('loadingSubtext');
const loadingSteps = document.getElementById('loadingSteps');
const statusPanel = document.getElementById('statusPanel');
const statusContent = document.getElementById('statusContent');
const analysisPanel = document.getElementById('analysisPanel');
const analysisContent = document.getElementById('analysisContent');
const itemPromptInput = document.getElementById('itemPrompt');
const toggleOptionsBtn = document.getElementById('toggleOptions');
const optionalFields = document.getElementById('optionalFields');
const examplesGrid = document.getElementById('examplesGrid');

// PERFORMANCE: Helper to convert Base64 to Blob URL (avoids massive string in DOM)
function base64ToBlobUrl(base64, type = 'image/png') {
    try {
        const binStr = atob(base64);
        const len = binStr.length;
        const arr = new Uint8Array(len);
        for (let i = 0; i < len; i++) {
            arr[i] = binStr.charCodeAt(i);
        }
        const blob = new Blob([arr], { type: type });
        return URL.createObjectURL(blob);
    } catch (e) {
        console.error('Error converting base64 to blob', e);
        return null;
    }
}

// Toggle optional fields
toggleOptionsBtn.addEventListener('click', () => {
    const isHidden = optionalFields.style.display === 'none';
    optionalFields.style.display = isHidden ? 'block' : 'none';
    toggleOptionsBtn.textContent = isHidden
        ? '⚙️ Hide Advanced Options'
        : '⚙️ Advanced Options (Optional)';
});

// PERFORMANCE: Event Delegation for Example Chips
// Instead of adding listeners to every single chip, we add one to the container.
examplesGrid.addEventListener('click', (e) => {
    // Check if user clicked a chip (or inside a chip)
    const chip = e.target.closest('.example-chip');
    
    if (chip) {
        const prompt = chip.dataset.prompt;
        itemPromptInput.value = prompt;
        itemPromptInput.focus();

        // Smooth scroll to textarea
        itemPromptInput.scrollIntoView({ behavior: 'smooth', block: 'center' });
    }
});

// Form Submission
modForm.addEventListener('submit', async (e) => {
    e.preventDefault();

    // Get form data
    const formData = new FormData(modForm);
    const data = {
        prompt: formData.get('itemPrompt').trim(),
        authorName: formData.get('authorName')?.trim() || null,
        modName: formData.get('modName')?.trim() || null
    };

    // Validate
    if (!data.prompt || data.prompt.length < 5) {
        showError('Please describe your item in at least a few words.');
        return;
    }

    // Hide previous results
    statusPanel.style.display = 'none';
    analysisPanel.style.display = 'none';

    // Show loading
    showLoading();

    try {
        // Call API to generate mod
        const result = await generateMod(data);

        // Clear progress animation
        clearProgressSteps();

        // Hide loading
        hideLoading();

        // Show success
        showSuccess(result);
    } catch (error) {
        // Clear progress animation
        clearProgressSteps();

        // Hide loading
        hideLoading();

        // Show error
        showError(error.message);
    }
});

// API Call to Generate Mod
async function generateMod(data) {
    // REAL API CALL TO BACKEND

    try {
        // Show progress steps
        simulateProgressSteps();

        const response = await fetch(`${API_BASE_URL}/generate-mod`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || error.detail || 'Failed to generate mod');
        }

        const result = await response.json();

        // Show AI analysis
        if (result.aiDecisions) {
            showAIAnalysis(result.aiDecisions);
        }

        return result;

    } catch (error) {
        console.error('API Error:', error);
        throw error;
    }
}

// Show progress steps (visual feedback while waiting for API)
function simulateProgressSteps() {
    const steps = [
        'Analyzing your prompt...',
        'AI is deciding item properties...',
        'Generating mod structure...',
        'Creating Java files...',
        'Generating assets...',
        'Compiling mod...'
    ];

    loadingSteps.innerHTML = steps.map((s, i) =>
        `<div class="loading-step" id="step-${i}">${s}</div>`
    ).join('');

    let currentStep = 0;
    const interval = setInterval(() => {
        if (currentStep < steps.length) {
            const stepEl = document.getElementById(`step-${currentStep}`);
            if (stepEl) {
                stepEl.classList.add('active');
            }
            currentStep++;
        }
    }, 2000);

    // Store interval ID to clear it later
    window.progressInterval = interval;
}

// Clear progress interval when done
function clearProgressSteps() {
    if (window.progressInterval) {
        clearInterval(window.progressInterval);
        window.progressInterval = null;
    }
}

// Show AI Analysis
function showAIAnalysis(decisions) {
    analysisPanel.style.display = 'block';

    const rarityColors = {
        'COMMON': 'white',
        'UNCOMMON': '#ffff55',
        'RARE': '#55ffff',
        'EPIC': '#ff55ff'
    };

    analysisContent.innerHTML = `
        <div class="analysis-item">
            <div class="analysis-label">🎯 AI Generated Mod Name:</div>
            <div class="analysis-value">${decisions.modName}</div>
        </div>

        <div class="analysis-item">
            <div class="analysis-label">✨ Item Name:</div>
            <div class="analysis-value">${decisions.itemName}</div>
        </div>

        <div class="analysis-grid">
            <div class="analysis-grid-item">
                <div class="analysis-grid-label">Mod ID</div>
                <div class="analysis-grid-value">${decisions.modId}</div>
            </div>
            <div class="analysis-grid-item">
                <div class="analysis-grid-label">Item ID</div>
                <div class="analysis-grid-value">${decisions.itemId}</div>
            </div>
            <div class="analysis-grid-item">
                <div class="analysis-grid-label">Max Stack Size</div>
                <div class="analysis-grid-value">${decisions.properties.maxStackSize}</div>
            </div>
            <div class="analysis-grid-item">
                <div class="analysis-grid-label">Rarity</div>
                <div class="analysis-grid-value" style="color: ${rarityColors[decisions.properties.rarity]}">${decisions.properties.rarity}</div>
            </div>
            <div class="analysis-grid-item">
                <div class="analysis-grid-label">Fireproof</div>
                <div class="analysis-grid-value">${decisions.properties.fireproof ? 'Yes 🔥' : 'No'}</div>
            </div>
            <div class="analysis-grid-item">
                <div class="analysis-grid-label">Creative Tab</div>
                <div class="analysis-grid-value">${decisions.properties.creativeTab.replace('_', ' ')}</div>
            </div>
        </div>

        <div class="analysis-item" style="margin-top: 15px;">
            <div class="analysis-label">📝 Description:</div>
            <div class="analysis-value" style="font-size: 12px; color: #aaa; font-style: italic;">${decisions.description}</div>
        </div>
    `;

    // Scroll to analysis
    analysisPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

// Show Loading Overlay
function showLoading() {
    loadingOverlay.style.display = 'flex';
    loadingSteps.innerHTML = '';
    loadingSubtext.textContent = 'Initializing AI...';
    generateBtn.disabled = true;
}

// Hide Loading Overlay
function hideLoading() {
    loadingOverlay.style.display = 'none';
    generateBtn.disabled = false;
}

// Show Success Message
function showSuccess(result) {
    statusPanel.style.display = 'block';

    const decisions = result.aiDecisions;
    const rarityColors = {
        'COMMON': 'white',
        'UNCOMMON': '#ffff55',
        'RARE': '#55ffff',
        'EPIC': '#ff55ff'
    };

    // PERFORMANCE: Use Blob URL instead of Base64 string in HTML
    let textureHtml = '';
    if (result.textureBase64) {
        const textureUrl = base64ToBlobUrl(result.textureBase64);
        if (textureUrl) {
            textureHtml = `
                <div class="texture-preview">
                    <div class="texture-preview-card">
                        <img
                            src="${textureUrl}"
                            alt="${decisions.itemName} texture"
                            class="texture-preview-image"
                        />
                        <div class="texture-preview-caption">AI Texture Preview</div>
                    </div>
                </div>
            `;
        }
    }

    const downloadHref = result.downloadUrl
        ? (result.downloadUrl.startsWith('http')
            ? result.downloadUrl
            : `${BACKEND_BASE_URL}${result.downloadUrl}`)
        : null;

    statusContent.innerHTML = `
        <div class="status-message status-success">
            <h3>✓ Mod Generated Successfully!</h3>
            <p style="margin-top: 10px;">Your custom Minecraft mod is ready to download.</p>
        </div>

        <div class="mod-details">
            <h3 style="margin-bottom: 15px; color: var(--mc-yellow);">📦 Mod Details</h3>

            <div class="mod-detail-row">
                <span class="mod-detail-label">Mod Name:</span>
                <span class="mod-detail-value">${decisions.modName}</span>
            </div>
            <div class="mod-detail-row">
                <span class="mod-detail-label">Mod ID:</span>
                <span class="mod-detail-value">${decisions.modId}</span>
            </div>
            <div class="mod-detail-row">
                <span class="mod-detail-label">Item Name:</span>
                <span class="mod-detail-value">${decisions.itemName}</span>
            </div>
            <div class="mod-detail-row">
                <span class="mod-detail-label">Item ID:</span>
                <span class="mod-detail-value">${decisions.itemId}</span>
            </div>
            <div class="mod-detail-row">
                <span class="mod-detail-label">Rarity:</span>
                <span class="mod-detail-value" style="color: ${rarityColors[decisions.properties.rarity]}">${decisions.properties.rarity}</span>
            </div>
            <div class="mod-detail-row">
                <span class="mod-detail-label">Max Stack:</span>
                <span class="mod-detail-value">${decisions.properties.maxStackSize}</span>
            </div>
            <div class="mod-detail-row">
                <span class="mod-detail-label">Fireproof:</span>
                <span class="mod-detail-value">${decisions.properties.fireproof ? 'Yes' : 'No'}</span>
            </div>
            <div class="mod-detail-row" style="border-bottom: none;">
                <span class="mod-detail-label">Creative Tab:</span>
                <span class="mod-detail-value">${decisions.properties.creativeTab.replace('_', ' ')}</span>
            </div>
        </div>

        ${textureHtml}

        ${downloadHref ? `
            <div class="download-button">
                <a href="${downloadHref}" download="${decisions.modId}.jar" class="btn btn-download">
                    <span class="btn-icon">⬇</span>
                    Download ${decisions.modName} (.jar)
                </a>
            </div>
        ` : ''}

        <div style="margin-top: 20px; text-align: center;">
            <button onclick="location.reload()" class="btn btn-primary">
                <span class="btn-icon">🔄</span>
                Create Another Mod
            </button>
        </div>
    `;

    // Scroll to status panel
    statusPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Show Error Message
function showError(message) {
    analysisPanel.style.display = 'none';
    statusPanel.style.display = 'block';
    statusContent.innerHTML = `
        <div class="status-message status-error">
            <h3>✗ Error</h3>
            <p>${message}</p>
        </div>
        <div style="margin-top: 20px; text-align: center;">
            <button onclick="hideStatusPanel()" class="btn btn-primary">
                <span class="btn-icon">←</span>
                Try Again
            </button>
        </div>
    `;

    // Scroll to status panel
    statusPanel.scrollIntoView({ behavior: 'smooth', block: 'center' });
}

// Hide Status Panel
function hideStatusPanel() {
    statusPanel.style.display = 'none';
    analysisPanel.style.display = 'none';
}

// Initialize
document.addEventListener('DOMContentLoaded', () => {
    console.log('Minecraft Mod Generator initialized (AI-powered mode)');

    // Focus on prompt input
    itemPromptInput.focus();
});

// Keyboard shortcuts
document.addEventListener('keydown', (e) => {
    // Ctrl/Cmd + Enter to submit form
    if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
        e.preventDefault();
        modForm.dispatchEvent(new Event('submit'));
    }
});

// Prevent accidental form submission on Enter in textarea
itemPromptInput.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.ctrlKey && !e.metaKey) {
        // Allow normal Enter for new lines in textarea
        // But Shift+Enter, Ctrl+Enter, Cmd+Enter have special behavior
    }
});
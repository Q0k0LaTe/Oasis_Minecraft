// Authentication module for Google OAuth and session management
const API_BASE_URL = 'http://localhost:3000/api';

// Global state
let currentSession = null;
let currentUser = null;
let pendingGoogleToken = null;

// DOM Elements (will be initialized in DOMContentLoaded)
let loginBtn = null;
let loginModal = null;
let closeLoginModal = null;
let usernameModal = null;
let usernameForm = null;
let usernameInput = null;
let submitUsernameBtn = null;
let userProfile = null;
let loginPrompt = null;
let userAvatar = null;
let userUsername = null;
let userStatus = null;

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    // Get DOM elements after page loads
    loginBtn = document.getElementById('loginBtn');
    loginModal = document.getElementById('loginModal');
    closeLoginModal = document.getElementById('closeLoginModal');
    usernameModal = document.getElementById('usernameModal');
    usernameForm = document.getElementById('usernameForm');
    usernameInput = document.getElementById('usernameInput');
    submitUsernameBtn = document.getElementById('submitUsernameBtn');
    userProfile = document.getElementById('userProfile');
    loginPrompt = document.getElementById('loginPrompt');
    userAvatar = document.getElementById('userAvatar');
    userUsername = document.getElementById('userUsername');
    userStatus = document.getElementById('userStatus');

    console.log('Auth module initialized', { loginBtn, loginModal });

    // Check for existing session
    const savedSession = localStorage.getItem('session_token');
    if (savedSession) {
        // Verify session is still valid (optional - could add endpoint for this)
        currentSession = savedSession;
        loadUserProfile();
    } else {
        showLoginPrompt();
    }

    // Note: Login button is now a link to login.html, no event listener needed

    if (closeLoginModal) {
        closeLoginModal.addEventListener('click', () => {
            hideLoginModal();
        });
    }

    if (usernameForm) {
        usernameForm.addEventListener('submit', handleUsernameSubmit);
    }

    // Close modals when clicking outside
    if (loginModal) {
        loginModal.addEventListener('click', (e) => {
            if (e.target === loginModal) {
                hideLoginModal();
            }
        });
    }

    if (usernameModal) {
        usernameModal.addEventListener('click', (e) => {
            if (e.target === usernameModal) {
                // Don't allow closing username modal - user must set username
            }
        });
    }

    // Initialize Google Sign-In
    initializeGoogleSignIn();
});

// Initialize Google Sign-In button
async function initializeGoogleSignIn() {
    // Wait for Google Identity Services to load
    if (typeof google !== 'undefined' && google.accounts) {
        const clientId = await getGoogleClientId();
        
        if (!clientId) {
            console.warn('Google Client ID not configured. Google Sign-In will not work.');
            const buttonContainer = document.getElementById('googleSignInButton');
            if (buttonContainer) {
                buttonContainer.innerHTML = '<p style="color: #888; font-size: 14px;">Google Sign-In not configured</p>';
            }
            return;
        }

        google.accounts.id.initialize({
            client_id: clientId,
            callback: handleGoogleSignIn,
        });

        google.accounts.id.renderButton(
            document.getElementById('googleSignInButton'),
            {
                theme: 'outline',
                size: 'large',
                width: '100%',
                text: 'signin_with',
                locale: 'en'
            }
        );
    } else {
        // Retry after a short delay
        setTimeout(initializeGoogleSignIn, 100);
    }
}

// Get Google Client ID from backend
let cachedGoogleClientId = null;

async function getGoogleClientId() {
    if (cachedGoogleClientId) {
        return cachedGoogleClientId;
    }

    try {
        const response = await fetch(`${API_BASE_URL}/auth/google-client-id`);
        if (response.ok) {
            const data = await response.json();
            cachedGoogleClientId = data.client_id;
            return cachedGoogleClientId;
        }
    } catch (error) {
        console.error('Failed to fetch Google Client ID:', error);
    }

    return '';
}

// Handle Google Sign-In callback
async function handleGoogleSignIn(response) {
    try {
        const idToken = response.credential;
        pendingGoogleToken = idToken;

        // Call backend to verify token and check if user exists
        const loginResponse = await fetch(`${API_BASE_URL}/auth/google-login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ id_token: idToken }),
        });

        if (!loginResponse.ok) {
            const error = await loginResponse.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await loginResponse.json();

        if (data.requires_username) {
            // First-time user - show username setup modal
            showUsernameModal();
        } else {
            // Existing user - login successful
            currentSession = data.session.token;
            currentUser = data.user;
            localStorage.setItem('session_token', currentSession);
            localStorage.setItem('user_info', JSON.stringify(currentUser));
            
            hideLoginModal();
            loadUserProfile();
        }
    } catch (error) {
        console.error('Google login error:', error);
        alert('Login failed: ' + error.message);
    }
}

// Handle username form submission
async function handleUsernameSubmit(e) {
    e.preventDefault();

    if (!pendingGoogleToken) {
        alert('Session expired. Please try logging in again.');
        return;
    }

    const username = usernameInput.value.trim();

    if (username.length < 3 || username.length > 50) {
        alert('Username must be between 3 and 50 characters.');
        return;
    }

    // Validate username format (letters, numbers, underscores only)
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        alert('Username can only contain letters, numbers, and underscores.');
        return;
    }

    try {
        submitUsernameBtn.disabled = true;
        submitUsernameBtn.textContent = 'Setting up...';

        const response = await fetch(`${API_BASE_URL}/auth/set-username`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                id_token: pendingGoogleToken,
                username: username,
            }),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to set username');
        }

        const data = await response.json();

        // Login successful
        currentSession = data.session.token;
        currentUser = data.user;
        localStorage.setItem('session_token', currentSession);
        localStorage.setItem('user_info', JSON.stringify(currentUser));

        pendingGoogleToken = null;
        hideUsernameModal();
        hideLoginModal();
        loadUserProfile();
    } catch (error) {
        console.error('Set username error:', error);
        alert('Failed to set username: ' + error.message);
        submitUsernameBtn.disabled = false;
        submitUsernameBtn.textContent = 'Continue';
    }
}

// Show login modal
function showLoginModal() {
    console.log('showLoginModal called', { loginModal });
    if (loginModal) {
        loginModal.style.display = 'flex';
        console.log('Login modal displayed');
    } else {
        console.error('Login modal element not found!');
    }
}

// Hide login modal
function hideLoginModal() {
    if (loginModal) {
        loginModal.style.display = 'none';
    }
}

// Show username modal
function showUsernameModal() {
    if (usernameModal) {
        usernameModal.style.display = 'flex';
        if (usernameInput) {
            usernameInput.focus();
        }
    }
}

// Hide username modal
function hideUsernameModal() {
    if (usernameModal) {
        usernameModal.style.display = 'none';
        if (usernameForm) {
            usernameForm.reset();
        }
    }
}

// Show login prompt
function showLoginPrompt() {
    console.log('showLoginPrompt called', { userProfile, loginPrompt });
    if (userProfile) {
        userProfile.style.display = 'none';
    }
    if (loginPrompt) {
        loginPrompt.style.display = 'block';
        console.log('Login prompt displayed');
    } else {
        console.error('Login prompt element not found!');
    }
}

// Load user profile
function loadUserProfile() {
    console.log('loadUserProfile called');
    // Try to get user info from localStorage
    const savedUserInfo = localStorage.getItem('user_info');
    if (savedUserInfo) {
        try {
            currentUser = JSON.parse(savedUserInfo);
            console.log('Loaded user from localStorage:', currentUser);
        } catch (e) {
            console.error('Failed to parse user info:', e);
        }
    }

    if (currentUser) {
        if (userProfile) {
            userProfile.style.display = 'block';
        }
        if (loginPrompt) {
            loginPrompt.style.display = 'none';
        }
        
        if (userUsername) {
            userUsername.textContent = currentUser.username || 'User';
        }
        
        // Set avatar (could use user.avatar_url if available)
        if (userAvatar) {
            userAvatar.textContent = (currentUser.username || 'U')[0].toUpperCase();
        }
        
        console.log('User profile loaded');
    } else {
        console.log('No user found, showing login prompt');
        showLoginPrompt();
    }
}

// Logout function
function logout() {
    currentSession = null;
    currentUser = null;
    pendingGoogleToken = null;
    localStorage.removeItem('session_token');
    localStorage.removeItem('user_info');
    showLoginPrompt();
}

// Export functions for use in other scripts
window.auth = {
    getSession: () => currentSession,
    getUser: () => currentUser,
    logout: logout,
    isAuthenticated: () => !!currentSession,
};


// Login page JavaScript
const API_BASE_URL = 'http://localhost:3000/api';

// Global state
let pendingGoogleToken = null;

// DOM Elements
const googleSignInButton = document.getElementById('googleSignInButton');
const emailLoginForm = document.getElementById('emailLoginForm');
const emailInput = document.getElementById('emailInput');
const passwordInput = document.getElementById('passwordInput');
const emailLoginBtn = document.getElementById('emailLoginBtn');
const registerBtn = document.getElementById('registerBtn');
const usernameModal = document.getElementById('usernameModal');
const usernameForm = document.getElementById('usernameForm');
const usernameInput = document.getElementById('usernameInput');
const submitUsernameBtn = document.getElementById('submitUsernameBtn');
const errorMessage = document.getElementById('errorMessage');
const successMessage = document.getElementById('successMessage');

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    console.log('Login page initialized');

    // Check if user is already logged in
    const savedSession = localStorage.getItem('session_token');
    if (savedSession) {
        console.log('User already logged in, redirecting...');
        window.location.href = 'index.html';
        return;
    }

    // Initialize Google Sign-In
    initializeGoogleSignIn();

    // Set up email login form
    if (emailLoginForm) {
        emailLoginForm.addEventListener('submit', handleEmailLogin);
    }

    // Set up register button
    if (registerBtn) {
        registerBtn.addEventListener('click', () => {
            showMessage('Registration feature coming soon. Please use Google Sign-In for now.', 'error');
        });
    }

    // Set up username form
    if (usernameForm) {
        usernameForm.addEventListener('submit', handleUsernameSubmit);
    }
});

// Initialize Google Sign-In button
async function initializeGoogleSignIn() {
    console.log('Initializing Google Sign-In...');
    
    // Wait for Google Identity Services to load
    if (typeof google !== 'undefined' && google.accounts) {
        const clientId = await getGoogleClientId();
        
        if (!clientId) {
            console.warn('Google Client ID not configured. Google Sign-In will not work.');
            if (googleSignInButton) {
                googleSignInButton.innerHTML = '<p style="color: #888; font-size: 14px; text-align: center;">Google Sign-In not configured</p>';
            }
            return;
        }

        console.log('Google Client ID loaded:', clientId.substring(0, 20) + '...');

        google.accounts.id.initialize({
            client_id: clientId,
            callback: handleGoogleSignIn,
        });

        if (googleSignInButton) {
            google.accounts.id.renderButton(
                googleSignInButton,
                {
                    theme: 'outline',
                    size: 'large',
                    width: '100%',
                    text: 'signin_with',
                    locale: 'en'
                }
            );
            console.log('Google Sign-In button rendered');
        }
    } else {
        // Retry after a short delay
        console.log('Google Identity Services not loaded yet, retrying...');
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
            console.log('Fetched Google Client ID from backend');
            return cachedGoogleClientId;
        } else {
            console.error('Failed to fetch Google Client ID:', response.status);
        }
    } catch (error) {
        console.error('Error fetching Google Client ID:', error);
    }

    return '';
}

// Handle Google Sign-In callback
async function handleGoogleSignIn(response) {
    console.log('Google Sign-In callback received');
    try {
        const idToken = response.credential;
        pendingGoogleToken = idToken;

        showMessage('Verifying Google account...', 'success');

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
            console.log('First-time user, showing username modal');
            showUsernameModal();
        } else {
            // Existing user - login successful
            console.log('Login successful, saving session');
            const sessionToken = data.session.token;
            const userInfo = data.user;
            
            localStorage.setItem('session_token', sessionToken);
            localStorage.setItem('user_info', JSON.stringify(userInfo));
            
            showMessage('Login successful! Redirecting...', 'success');
            
            // Redirect to main page after a short delay
            setTimeout(() => {
                window.location.href = 'index.html';
            }, 1000);
        }
    } catch (error) {
        console.error('Google login error:', error);
        showMessage('Login failed: ' + error.message, 'error');
    }
}

// Handle email login form submission
async function handleEmailLogin(e) {
    e.preventDefault();
    console.log('Email login form submitted');

    const emailOrUsername = emailInput.value.trim();
    const password = passwordInput.value;

    if (!emailOrUsername || !password) {
        showMessage('Please enter both email/username and password', 'error');
        return;
    }

    try {
        emailLoginBtn.disabled = true;
        emailLoginBtn.textContent = 'Logging in...';
        showMessage('Logging in...', 'success');

        // Determine if input is email or username
        const isEmail = emailOrUsername.includes('@');
        const requestBody = isEmail 
            ? { email: emailOrUsername, password: password }
            : { username: emailOrUsername, password: password };

        const response = await fetch(`${API_BASE_URL}/auth/login`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(requestBody),
        });

        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }

        const data = await response.json();

        // Login successful
        console.log('Email login successful');
        const sessionToken = data.session.token;
        const userInfo = data.user;
        
        localStorage.setItem('session_token', sessionToken);
        localStorage.setItem('user_info', JSON.stringify(userInfo));
        
        showMessage('Login successful! Redirecting...', 'success');
        
        // Redirect to main page after a short delay
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);

    } catch (error) {
        console.error('Email login error:', error);
        showMessage('Login failed: ' + error.message, 'error');
        emailLoginBtn.disabled = false;
        emailLoginBtn.textContent = 'Login';
    }
}

// Handle username form submission
async function handleUsernameSubmit(e) {
    e.preventDefault();
    console.log('Username form submitted');

    if (!pendingGoogleToken) {
        showMessage('Session expired. Please try logging in again.', 'error');
        return;
    }

    const username = usernameInput.value.trim();

    if (username.length < 3 || username.length > 50) {
        showMessage('Username must be between 3 and 50 characters.', 'error');
        return;
    }

    // Validate username format (letters, numbers, underscores only)
    if (!/^[a-zA-Z0-9_]+$/.test(username)) {
        showMessage('Username can only contain letters, numbers, and underscores.', 'error');
        return;
    }

    try {
        submitUsernameBtn.disabled = true;
        submitUsernameBtn.textContent = 'Setting up...';
        showMessage('Setting up your account...', 'success');

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

        // Registration successful
        console.log('Username set successfully');
        const sessionToken = data.session.token;
        const userInfo = data.user;
        
        localStorage.setItem('session_token', sessionToken);
        localStorage.setItem('user_info', JSON.stringify(userInfo));

        pendingGoogleToken = null;
        hideUsernameModal();
        showMessage('Account created successfully! Redirecting...', 'success');
        
        // Redirect to main page after a short delay
        setTimeout(() => {
            window.location.href = 'index.html';
        }, 1000);

    } catch (error) {
        console.error('Set username error:', error);
        showMessage('Failed to set username: ' + error.message, 'error');
        submitUsernameBtn.disabled = false;
        submitUsernameBtn.textContent = 'Continue';
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

// Show message
function showMessage(message, type) {
    if (type === 'error') {
        if (errorMessage) {
            errorMessage.textContent = message;
            errorMessage.classList.add('show');
            successMessage.classList.remove('show');
        }
    } else {
        if (successMessage) {
            successMessage.textContent = message;
            successMessage.classList.add('show');
            errorMessage.classList.remove('show');
        }
    }
}


const API_URL = window.location.origin;

// Safe JSON parse helper
async function safeJSON(response) {
    const contentType = response.headers.get('content-type');
    if (contentType && contentType.includes('application/json')) {
        return await response.json();
    }
    const text = await response.text();
    throw new Error(text || `Server error: ${response.status}`);
}

async function register(username, password, full_name, student_id, email, department, semester, profile_image) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);
    formData.append('full_name', full_name);
    formData.append('student_id', student_id);
    formData.append('email', email);
    formData.append('department', department);
    formData.append('semester', semester);
    if (profile_image) formData.append('profile_image', profile_image);

    try {
        const response = await fetch(`${API_URL}/register`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            return true;
        } else {
            const error = await safeJSON(response);
            throw new Error(error.detail || 'Registration failed');
        }
    } catch (err) {
        throw new Error(err.message || 'Network error - please try again');
    }
}

async function login(username, password) {
    const formData = new FormData();
    formData.append('username', username);
    formData.append('password', password);

    try {
        const response = await fetch(`${API_URL}/token`, {
            method: 'POST',
            body: formData
        });

        if (response.ok) {
            const data = await safeJSON(response);
            localStorage.setItem('token', data.access_token);
            localStorage.setItem('username', data.username);
            localStorage.setItem('profile_image', data.profile_image || '');
            localStorage.setItem('is_admin', data.is_admin ? 'true' : 'false');
            
            // Remember username if requested
            const rememberMe = document.getElementById('rememberMe')?.checked;
            if (rememberMe) {
                localStorage.setItem('remembered_username', username);
            } else {
                localStorage.removeItem('remembered_username');
            }
            
            return true;
        } else {
            const error = await safeJSON(response);
            throw new Error(error.detail || 'Invalid credentials');
        }
    } catch (err) {
        throw new Error(err.message || 'Network error - please try again');
    }
}

function logout() {
    // Clear all auth data
    localStorage.removeItem('token');
    localStorage.removeItem('username');
    localStorage.removeItem('profile_image');
    localStorage.removeItem('is_admin');
    
    // Redirect to login
    window.location.href = '/login.html';
}

// Check if user is authenticated
function isAuthenticated() {
    return !!localStorage.getItem('token');
}

// Check if user is admin
function isAdmin() {
    return localStorage.getItem('is_admin') === 'true';
}

// Get auth headers for API requests
function getAuthHeaders() {
    const token = localStorage.getItem('token');
    return token ? { 'Authorization': `Bearer ${token}` } : {};
}

document.addEventListener('DOMContentLoaded', () => {
    // Utility functions to manage local session storage
    const getToken = () => localStorage.getItem('token');
    const getUsername = () => localStorage.getItem('username');
    const setSession = (token, username) => {
        localStorage.setItem('token', token);
        localStorage.setItem('username', username);
    };
    const clearSession = () => {
        localStorage.removeItem('token');
        localStorage.removeItem('username');
    };

    // Determine current page
    const path = window.location.pathname;
    const pageName = path.substring(path.lastIndexOf('/') + 1) || 'index.html';

    // Inject Background Animation on all pages
    const bgAnim = document.createElement('div');
    bgAnim.className = 'background-animation';
    document.body.appendChild(bgAnim);

    // List of page classifications
    const authPages = ['login.html', 'register.html'];
    const protectedPages = ['dashboard.html', 'generator.html'];

    // Session Guards
    if (protectedPages.includes(pageName)) {
        if (!getToken()) {
            window.location.href = 'login.html';
            return;
        }
    } else if (authPages.includes(pageName)) {
        if (getToken()) {
            window.location.href = 'dashboard.html';
            return;
        }
    }

    // Flash Message Helper
    window.showFlashMessage = (message, type = 'success') => {
        let container = document.querySelector('.flash-messages');
        if (!container) {
            container = document.createElement('div');
            container.className = 'flash-messages';
            const mainContainer = document.querySelector('.container');
            if (mainContainer) {
                mainContainer.insertBefore(container, mainContainer.firstChild);
            } else {
                document.body.insertBefore(container, document.body.firstChild);
            }
        }
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type === 'error' ? 'error' : 'success'} glassmorphism slide-in`;
        alertDiv.textContent = message;
        container.appendChild(alertDiv);

        setTimeout(() => {
            alertDiv.style.opacity = '0';
            alertDiv.style.transition = 'opacity 0.4s ease';
            setTimeout(() => alertDiv.remove(), 400);
        }, 4000);
    };

    // Logout Handler
    const handleLogout = async () => {
        const token = getToken();
        if (token) {
            try {
                await fetch(`${API_BASE_URL}/api/logout`, {
                    method: 'POST',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });
            } catch (err) {
                console.error("Logout request error:", err);
            }
        }
        clearSession();
        window.location.href = 'login.html';
    };

    // Inject Navigation Bar for Protected Pages
    if (protectedPages.includes(pageName)) {
        const activeItem = pageName === 'dashboard.html' ? 'dashboard' : 'generator';
        const navbar = document.createElement('nav');
        navbar.className = 'navbar glassmorphism';
        navbar.innerHTML = `
            <div class="nav-brand">
                <i class="fa-solid fa-envelope-open-text"></i>
                <span>AI Email Gen</span>
            </div>
            <div class="nav-links">
                <a href="dashboard.html" class="nav-link ${activeItem === 'dashboard' ? 'active' : ''}"><i class="fa-solid fa-chart-line"></i> Dashboard</a>
                <a href="generator.html" class="nav-link ${activeItem === 'generator' ? 'active' : ''}"><i class="fa-solid fa-wand-magic-sparkles"></i> Generator</a>
                <a href="#" id="logoutBtn" class="nav-link logout-btn"><i class="fa-solid fa-right-from-bracket"></i> Logout</a>
            </div>
        `;
        document.body.insertBefore(navbar, document.body.firstChild);

        document.getElementById('logoutBtn').addEventListener('click', (e) => {
            e.preventDefault();
            handleLogout();
        });
    }

    // --- 1. Login Page Logic ---
    if (pageName === 'login.html') {
        // Show registration success message if redirected from register
        const urlParams = new URLSearchParams(window.location.search);
        if (urlParams.get('registered') === 'true') {
            window.showFlashMessage('Registration successful! Please login.', 'success');
        }

        const loginForm = document.querySelector('.auth-form');
        if (loginForm) {
            loginForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const usernameInput = document.getElementById('username').value.trim();
                const passwordInput = document.getElementById('password').value.trim();
                
                try {
                    const response = await fetch(`${API_BASE_URL}/api/login`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            username: usernameInput,
                            password: passwordInput
                        })
                    });
                    const data = await response.json();
                    if (response.ok && data.success) {
                        setSession(data.token, data.username);
                        window.location.href = 'dashboard.html';
                    } else {
                        window.showFlashMessage(data.error || 'Invalid username or password!', 'error');
                    }
                } catch (err) {
                    console.error("Login fetch error:", err);
                    window.showFlashMessage('Failed to connect to backend server.', 'error');
                }
            });
        }
    }

    // --- 2. Register Page Logic ---
    if (pageName === 'register.html') {
        const registerForm = document.querySelector('.auth-form');
        if (registerForm) {
            registerForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                const usernameInput = document.getElementById('username').value.trim();
                const passwordInput = document.getElementById('password').value.trim();

                try {
                    const response = await fetch(`${API_BASE_URL}/api/register`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify({
                            username: usernameInput,
                            password: passwordInput
                        })
                    });
                    const data = await response.json();
                    if (response.ok && data.success) {
                        window.location.href = 'login.html?registered=true';
                    } else {
                        window.showFlashMessage(data.error || 'Registration failed!', 'error');
                    }
                } catch (err) {
                    console.error("Registration fetch error:", err);
                    window.showFlashMessage('Failed to connect to backend server.', 'error');
                }
            });
        }
    }

    // --- 3. Dashboard Page Logic ---
    if (pageName === 'dashboard.html') {
        // Set Username greeting
        const welcomeSpan = document.querySelector('.welcome-section .highlight');
        if (welcomeSpan) {
            welcomeSpan.textContent = getUsername() || 'User';
        }

        const emailGrid = document.querySelector('.email-grid');
        const emptyState = document.querySelector('.empty-state');
        const historySection = document.querySelector('.history-section');

        const loadEmails = async (searchQuery = '') => {
            const token = getToken();
            try {
                let url = `${API_BASE_URL}/api/dashboard`;
                if (searchQuery) {
                    url += `?search=${encodeURIComponent(searchQuery)}`;
                }
                const response = await fetch(url, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${token}`
                    }
                });

                if (response.status === 401) {
                    clearSession();
                    window.location.href = 'login.html';
                    return;
                }

                const data = await response.json();
                if (response.ok && data.success) {
                    renderEmails(data.emails, searchQuery);
                } else {
                    window.showFlashMessage('Failed to load dashboard data.', 'error');
                }
            } catch (err) {
                console.error("Dashboard fetch error:", err);
                window.showFlashMessage('Could not load email history.', 'error');
            }
        };

        const renderEmails = (emails, searchQuery = '') => {
            // Clear existing grid contents
            if (emailGrid) {
                emailGrid.innerHTML = '';
            }

            if (emails && emails.length > 0) {
                if (emptyState) emptyState.style.display = 'none';
                if (emailGrid) emailGrid.style.display = 'grid';

                emails.forEach(email => {
                    const card = document.createElement('div');
                    card.className = 'email-card glassmorphism';
                    
                    const badgeClass = `type-${email.type.replace(/_/g, '-')}`;
                    const formattedType = email.type.replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase());
                    const shortDate = email.created_at.substring(0, 10);
                    const shortPurpose = email.purpose.length > 60 ? email.purpose.substring(0, 60) + '...' : email.purpose;

                    card.innerHTML = `
                        <div class="email-card-header">
                            <span class="badge ${badgeClass}">${formattedType}</span>
                            <span class="date"><i class="fa-regular fa-calendar"></i> ${shortDate}</span>
                        </div>
                        <h4 class="email-subject">${escapeHtml(email.subject)}</h4>
                        <p class="email-purpose">${escapeHtml(shortPurpose)}</p>
                        <div class="email-actions">
                            <button class="btn btn-sm btn-outline copy-history-btn" data-content="${escapeAttr(email.content)}">
                                <i class="fa-regular fa-copy"></i> Copy
                            </button>
                            <button class="btn btn-sm btn-outline view-history-btn" data-subject="${escapeAttr(email.subject)}" data-content="${escapeAttr(email.content)}">
                                <i class="fa-regular fa-eye"></i> View
                            </button>
                        </div>
                    `;
                    emailGrid.appendChild(card);
                });

                // Attach copy and view listeners to new DOM elements
                attachHistoryBtnListeners();
            } else {
                if (emailGrid) emailGrid.style.display = 'none';
                
                // Construct empty state
                let emptyHTML = '';
                if (searchQuery) {
                    emptyHTML = `
                        <i class="fa-regular fa-folder-open fa-3x"></i>
                        <h3>No emails found</h3>
                        <p>We couldn't find any emails matching "${escapeHtml(searchQuery)}".</p>
                    `;
                } else {
                    emptyHTML = `
                        <i class="fa-regular fa-folder-open fa-3x"></i>
                        <h3>No emails yet</h3>
                        <p>You haven't generated any emails. Head over to the generator to create your first one!</p>
                        <a href="generator.html" class="btn btn-primary mt-3">Start Generating</a>
                    `;
                }
                
                if (emptyState) {
                    emptyState.innerHTML = emptyHTML;
                    emptyState.style.display = 'block';
                } else {
                    const newEmptyState = document.createElement('div');
                    newEmptyState.className = 'empty-state glassmorphism';
                    newEmptyState.innerHTML = emptyHTML;
                    historySection.appendChild(newEmptyState);
                }
            }
        };

        const attachHistoryBtnListeners = () => {
            // Copy buttons
            const copyHistoryBtns = document.querySelectorAll('.copy-history-btn');
            copyHistoryBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    const content = btn.getAttribute('data-content');
                    navigator.clipboard.writeText(content).then(() => {
                        const originalHtml = btn.innerHTML;
                        btn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                        setTimeout(() => {
                            btn.innerHTML = originalHtml;
                        }, 2000);
                    });
                });
            });

            // View buttons
            const viewBtns = document.querySelectorAll('.view-history-btn');
            const modal = document.getElementById('viewModal');
            const modalSubject = document.getElementById('modalSubject');
            const modalContent = document.getElementById('modalContent');

            viewBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    if (modal && modalSubject && modalContent) {
                        modalSubject.textContent = btn.getAttribute('data-subject');
                        modalContent.textContent = btn.getAttribute('data-content');
                        modal.style.display = 'flex';
                    }
                });
            });
        };

        // Hook up search form
        const searchForm = document.querySelector('.search-form');
        if (searchForm) {
            searchForm.addEventListener('submit', (e) => {
                e.preventDefault();
                const searchInput = searchForm.querySelector('input[name="search"]');
                const query = searchInput ? searchInput.value.trim() : '';
                loadEmails(query);

                // Add or update clear button
                let clearBtn = searchForm.querySelector('.clear-search');
                if (query) {
                    if (!clearBtn) {
                        const wrapper = searchForm.querySelector('.search-input-wrapper');
                        clearBtn = document.createElement('a');
                        clearBtn.className = 'clear-search';
                        clearBtn.href = '#';
                        clearBtn.innerHTML = '<i class="fa-solid fa-times"></i>';
                        wrapper.appendChild(clearBtn);
                        
                        clearBtn.addEventListener('click', (ev) => {
                            ev.preventDefault();
                            searchInput.value = '';
                            clearBtn.remove();
                            loadEmails('');
                        });
                    }
                } else {
                    if (clearBtn) clearBtn.remove();
                }
            });
        }

        // View Modal closure
        const modal = document.getElementById('viewModal');
        if (modal) {
            const closeBtn = document.querySelector('.close-modal');
            if (closeBtn) {
                closeBtn.addEventListener('click', () => {
                    modal.style.display = 'none';
                });
            }
            window.addEventListener('click', (e) => {
                if (e.target === modal) {
                    modal.style.display = 'none';
                }
            });
        }

        // Initial Load
        loadEmails();
    }

    // --- 4. Generator Page Logic ---
    if (pageName === 'generator.html') {
        // Tab switching
        const tabBtns = document.querySelectorAll('.tab-btn');
        const tabContents = document.querySelectorAll('.tab-content');

        tabBtns.forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                tabBtns.forEach(b => b.classList.remove('active'));
                tabContents.forEach(c => c.style.display = 'none');
                
                btn.classList.add('active');
                const targetId = btn.getAttribute('data-target');
                document.getElementById(targetId).style.display = 'block';
            });
        });

        // Form Submission
        const generatorForm = document.getElementById('generatorForm');
        if (generatorForm) {
            generatorForm.addEventListener('submit', async (e) => {
                e.preventDefault();
                
                const btn = document.getElementById('generateBtn');
                const btnText = btn.querySelector('.btn-text');
                const loader = btn.querySelector('.loader');
                
                // Loading state
                btn.disabled = true;
                btnText.style.display = 'none';
                loader.style.display = 'inline-block';
                
                // Prepare payload
                const isThread = document.querySelector('.tab-btn.active').getAttribute('data-target') === 'thread-email';
                const payload = {
                    type: document.getElementById('emailType').value,
                    subject: document.getElementById('subject').value.trim(),
                    purpose: document.getElementById('purpose').value.trim(),
                    is_thread: isThread,
                    thread_type: document.getElementById('threadType').value
                };

                const token = getToken();
                try {
                    const response = await fetch(`${API_BASE_URL}/api/generate`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Authorization': `Bearer ${token}`
                        },
                        body: JSON.stringify(payload)
                    });

                    if (response.status === 401) {
                        clearSession();
                        window.location.href = 'login.html';
                        return;
                    }

                    const data = await response.json();
                    if (response.ok && data.success) {
                        document.getElementById('emptyResult').style.display = 'none';
                        document.getElementById('activeResult').style.display = 'flex';
                        
                        document.getElementById('resultSubject').textContent = data.subject;
                        document.getElementById('resultContent').textContent = data.content;
                        
                        document.getElementById('copyBtn').disabled = false;
                        window.showFlashMessage('Email generated successfully!', 'success');
                    } else {
                        window.showFlashMessage(data.error || 'Failed to generate email.', 'error');
                    }
                } catch (error) {
                    console.error("Generation error:", error);
                    window.showFlashMessage('Failed to connect to backend server.', 'error');
                } finally {
                    btn.disabled = false;
                    btnText.style.display = 'inline-block';
                    loader.style.display = 'none';
                }
            });
        }

        // Copy functionality
        const copyBtn = document.getElementById('copyBtn');
        if (copyBtn) {
            copyBtn.addEventListener('click', () => {
                const subject = document.getElementById('resultSubject').textContent;
                const content = document.getElementById('resultContent').textContent;
                const textToCopy = `Subject: ${subject}\n\n${content}`;
                
                navigator.clipboard.writeText(textToCopy).then(() => {
                    const originalHtml = copyBtn.innerHTML;
                    copyBtn.innerHTML = '<i class="fa-solid fa-check"></i> Copied!';
                    copyBtn.classList.add('btn-success');
                    
                    setTimeout(() => {
                        copyBtn.innerHTML = originalHtml;
                        copyBtn.classList.remove('btn-success');
                    }, 2000);
                });
            });
        }
    }

    // HTML escape helpers to prevent XSS injection
    function escapeHtml(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;");
    }

    function escapeAttr(str) {
        if (!str) return '';
        return str
            .replace(/&/g, "&amp;")
            .replace(/"/g, "&quot;")
            .replace(/'/g, "&#039;")
            .replace(/</g, "&lt;")
            .replace(/>/g, "&gt;");
    }
});

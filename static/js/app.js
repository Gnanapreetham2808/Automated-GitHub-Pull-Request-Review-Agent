// API Base URL
const API_BASE = '';

// Tab Switching
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove active class from all tabs
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        document.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
        
        // Add active class to clicked tab
        btn.classList.add('active');
        const tabId = btn.dataset.tab + '-tab';
        document.getElementById(tabId).classList.add('active');
    });
});

// Manual Diff Form Submission
document.getElementById('manual-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const diff = document.getElementById('diff-input').value;
    const btn = e.target.querySelector('button[type="submit"]');
    
    // Show loading state
    setButtonLoading(btn, true);
    hideError();
    hideResults();
    
    try {
        const response = await fetch(`${API_BASE}/review/manual`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ diff })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to analyze diff');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        setButtonLoading(btn, false);
    }
});

// GitHub PR Form Submission
document.getElementById('github-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    const owner = document.getElementById('owner-input').value;
    const repo = document.getElementById('repo-input').value;
    const pr = parseInt(document.getElementById('pr-input').value);
    const btn = e.target.querySelector('button[type="submit"]');
    
    // Show loading state
    setButtonLoading(btn, true);
    hideError();
    hideResults();
    
    try {
        const response = await fetch(`${API_BASE}/review/github`, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ owner, repo, pr })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Failed to review PR');
        }
        
        const data = await response.json();
        displayResults(data);
        
    } catch (error) {
        showError(error.message);
    } finally {
        setButtonLoading(btn, false);
    }
});

// Clear Results
document.getElementById('clear-results').addEventListener('click', () => {
    hideResults();
    document.getElementById('diff-input').value = '';
    document.getElementById('owner-input').value = '';
    document.getElementById('repo-input').value = '';
    document.getElementById('pr-input').value = '';
});

// Helper Functions
function setButtonLoading(btn, loading) {
    const textSpan = btn.querySelector('.btn-text');
    const loadingSpan = btn.querySelector('.btn-loading');
    
    if (loading) {
        textSpan.style.display = 'none';
        loadingSpan.style.display = 'flex';
        btn.disabled = true;
    } else {
        textSpan.style.display = 'block';
        loadingSpan.style.display = 'none';
        btn.disabled = false;
    }
}

function showError(message) {
    const errorEl = document.getElementById('error-message');
    errorEl.textContent = message;
    errorEl.style.display = 'block';
    errorEl.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
}

function hideError() {
    document.getElementById('error-message').style.display = 'none';
}

function hideResults() {
    document.getElementById('results').style.display = 'none';
}

function displayResults(data) {
    const resultsEl = document.getElementById('results');
    const commentsContainer = document.getElementById('comments-container');
    
    // Show results section
    resultsEl.style.display = 'block';
    
    // Display summary if available
    if (data.summary) {
        document.getElementById('summary-section').style.display = 'flex';
        document.getElementById('summary-text').textContent = data.summary;
    } else {
        document.getElementById('summary-section').style.display = 'none';
    }
    
    // Calculate stats
    const stats = calculateStats(data.comments);
    document.getElementById('total-comments').textContent = stats.total;
    document.getElementById('logic-count').textContent = stats.logic;
    document.getElementById('style-count').textContent = stats.style;
    document.getElementById('security-count').textContent = stats.security;
    document.getElementById('performance-count').textContent = stats.performance;
    
    // Display comments
    commentsContainer.innerHTML = '';
    
    if (data.comments.length === 0) {
        commentsContainer.innerHTML = `
            <div class="comment-card" style="text-align: center; padding: 48px;">
                <svg width="64" height="64" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="margin: 0 auto 16px; color: var(--success);">
                    <path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/>
                    <polyline points="22 4 12 14.01 9 11.01"/>
                </svg>
                <h3 style="margin-bottom: 8px;">No Issues Found!</h3>
                <p style="color: var(--text-secondary);">The code review didn't find any significant issues.</p>
            </div>
        `;
    } else {
        data.comments.forEach(comment => {
            const card = createCommentCard(comment);
            commentsContainer.appendChild(card);
        });
    }
    
    // Scroll to results
    resultsEl.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function calculateStats(comments) {
    const stats = {
        total: comments.length,
        logic: 0,
        style: 0,
        security: 0,
        performance: 0
    };
    
    comments.forEach(comment => {
        const category = comment.category.toLowerCase();
        if (stats.hasOwnProperty(category)) {
            stats[category]++;
        }
    });
    
    return stats;
}

function createCommentCard(comment) {
    const card = document.createElement('div');
    card.className = 'comment-card';
    
    const confidenceClass = getConfidenceClass(comment.confidence);
    const confidenceLabel = getConfidenceLabel(comment.confidence);
    
    card.innerHTML = `
        <div class="comment-header">
            <div class="comment-meta">
                <span class="category-badge ${comment.category.toLowerCase()}">
                    ${getCategoryIcon(comment.category)}
                    ${comment.category}
                </span>
                <span class="file-location">
                    ${comment.path}:${comment.line}
                </span>
            </div>
            <span class="confidence-badge ${confidenceClass}">
                ${(comment.confidence * 100).toFixed(0)}% ${confidenceLabel}
            </span>
        </div>
        <div class="comment-body">${escapeHtml(comment.body)}</div>
    `;
    
    return card;
}

function getCategoryIcon(category) {
    const icons = {
        logic: '🧠',
        style: '✨',
        security: '🔒',
        performance: '⚡'
    };
    return icons[category.toLowerCase()] || '📝';
}

function getConfidenceClass(confidence) {
    if (confidence >= 0.8) return 'confidence-high';
    if (confidence >= 0.5) return 'confidence-medium';
    return 'confidence-low';
}

function getConfidenceLabel(confidence) {
    if (confidence >= 0.8) return 'High';
    if (confidence >= 0.5) return 'Medium';
    return 'Low';
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Smooth scrolling for anchor links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
        }
    });
});

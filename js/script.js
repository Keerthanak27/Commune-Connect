// Enhanced JavaScript functionality

// Initialize tooltips
function initTooltips() {
    const tooltips = document.querySelectorAll('[data-toggle="tooltip"]');
    tooltips.forEach(tooltip => {
        tooltip.addEventListener('mouseenter', function() {
            // Tooltip implementation
        });
    });
}

// Form validation enhancement
function enhanceFormValidation() {
    const forms = document.querySelectorAll('form');
    forms.forEach(form => {
        form.addEventListener('submit', function(e) {
            const requiredFields = form.querySelectorAll('[required]');
            let valid = true;
            
            requiredFields.forEach(field => {
                if (!field.value.trim()) {
                    field.style.borderColor = 'var(--danger)';
                    valid = false;
                } else {
                    field.style.borderColor = '';
                }
            });
            
            if (!valid) {
                e.preventDefault();
                showNotification('Please fill all required fields', 'error');
            }
        });
    });
}

// Notification system
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `notification notification-${type}`;
    notification.innerHTML = `
        <span>${message}</span>
        <button onclick="this.parentElement.remove()">&times;</button>
    `;
    
    // Add styles
    notification.style.cssText = `
        position: fixed;
        top: 20px;
        right: 20px;
        padding: 1rem 1.5rem;
        background: ${type === 'error' ? 'var(--danger)' : type === 'success' ? 'var(--success)' : 'var(--info)'};
        color: white;
        border-radius: var(--radius);
        box-shadow: var(--shadow);
        z-index: 10000;
        display: flex;
        align-items: center;
        gap: 1rem;
        animation: slideIn 0.3s ease-out;
    `;
    
    document.body.appendChild(notification);
    
    setTimeout(() => {
        if (notification.parentElement) {
            notification.remove();
        }
    }, 5000);
}

// Image lazy loading
function initLazyLoading() {
    const images = document.querySelectorAll('img[data-src]');
    
    const imageObserver = new IntersectionObserver((entries, observer) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                const img = entry.target;
                img.src = img.dataset.src;
                img.classList.remove('lazy');
                imageObserver.unobserve(img);
            }
        });
    });
    
    images.forEach(img => imageObserver.observe(img));
}

// Search functionality enhancement
function enhanceSearch() {
    const searchInputs = document.querySelectorAll('.search-input');
    
    searchInputs.forEach(input => {
        input.addEventListener('input', debounce(function() {
            // Perform search operations
            const tableId = this.dataset.table;
            if (tableId) {
                searchTable(tableId, this.value);
            }
        }, 300));
    });
}

// Debounce function for performance
function debounce(func, wait) {
    let timeout;
    return function executedFunction(...args) {
        const later = () => {
            clearTimeout(timeout);
            func(...args);
        };
        clearTimeout(timeout);
        timeout = setTimeout(later, wait);
    };
}

// Password strength checker
function initPasswordStrength() {
    const passwordInputs = document.querySelectorAll('input[type="password"]');
    
    passwordInputs.forEach(input => {
        input.addEventListener('input', function() {
            const strengthIndicator = this.parentElement.querySelector('.password-strength');
            if (strengthIndicator) {
                const strength = checkPasswordStrength(this.value);
                strengthIndicator.textContent = strength.text;
                strengthIndicator.style.color = strength.color;
            }
        });
    });
}

function checkPasswordStrength(password) {
    let strength = 0;
    
    if (password.length >= 8) strength++;
    if (/[a-z]/.test(password)) strength++;
    if (/[A-Z]/.test(password)) strength++;
    if (/[0-9]/.test(password)) strength++;
    if (/[^a-zA-Z0-9]/.test(password)) strength++;
    
    const levels = [
        { text: 'Very Weak', color: 'var(--danger)' },
        { text: 'Weak', color: 'var(--warning)' },
        { text: 'Fair', color: 'var(--info)' },
        { text: 'Good', color: 'var(--success)' },
        { text: 'Strong', color: 'var(--success)' }
    ];
    
    return levels[Math.min(strength, levels.length - 1)];
}

// Initialize everything when DOM is loaded
document.addEventListener('DOMContentLoaded', function() {
    initTooltips();
    enhanceFormValidation();
    initLazyLoading();
    enhanceSearch();
    initPasswordStrength();
    
    // Add fade-in animation to cards
    const cards = document.querySelectorAll('.card');
    cards.forEach((card, index) => {
        card.style.animationDelay = `${index * 0.1}s`;
        card.classList.add('fade-in');
    });
});

// Export functions for global use
window.showNotification = showNotification;
window.debounce = debounce;
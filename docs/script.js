// Mobile Menu Toggle
const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
const navMenu = document.querySelector('.nav-menu');

if (mobileMenuToggle) {
    mobileMenuToggle.addEventListener('click', () => {
        navMenu.classList.toggle('active');
        mobileMenuToggle.classList.toggle('active');
    });
}

// Smooth Scroll for Navigation Links
document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
        e.preventDefault();
        const target = document.querySelector(this.getAttribute('href'));
        if (target) {
            target.scrollIntoView({
                behavior: 'smooth',
                block: 'start'
            });
            // Close mobile menu if open
            if (navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
            }
        }
    });
});

// Navbar Background on Scroll
const navbar = document.querySelector('.navbar');
let lastScroll = 0;

window.addEventListener('scroll', () => {
    const currentScroll = window.pageYOffset;
    
    if (currentScroll > 100) {
        navbar.style.background = 'rgba(15, 20, 25, 0.95)';
        navbar.style.boxShadow = '0 4px 20px rgba(0, 0, 0, 0.3)';
    } else {
        navbar.style.background = 'rgba(15, 20, 25, 0.9)';
        navbar.style.boxShadow = 'none';
    }
    
    lastScroll = currentScroll;
});

// Intersection Observer for Animations
const observerOptions = {
    threshold: 0.1,
    rootMargin: '0px 0px -50px 0px'
};

const observer = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            entry.target.style.opacity = '1';
            entry.target.style.transform = 'translateY(0)';
        }
    });
}, observerOptions);

// Observe all animated elements
document.querySelectorAll('.feature-card, .installer-card, .spec-item, .step, .app-category').forEach(el => {
    el.style.opacity = '0';
    el.style.transform = 'translateY(30px)';
    el.style.transition = 'opacity 0.6s ease-out, transform 0.6s ease-out';
    observer.observe(el);
});

// Terminal Animation
const terminalCommands = [
    { delay: 1000, text: '$ sudo install-mados', clear: false },
    { delay: 2000, text: '\n╔══════════════════════════════════════╗', clear: false },
    { delay: 2100, text: '\n║    madOS Installation Manager        ║', clear: false },
    { delay: 2200, text: '\n╚══════════════════════════════════════╝', clear: false },
    { delay: 3000, text: '\n\n<span class="terminal-success">✓</span> Detecting environment...', clear: false },
    { delay: 3500, text: '\n<span class="terminal-success">✓</span> Starting GTK installer', clear: false },
    { delay: 4000, text: '\n<span class="terminal-success">✓</span> AI optimization enabled', clear: false },
    { delay: 4500, text: '\n\n<span class="terminal-info">→ Ready to install madOS!</span>', clear: false }
];

// Copy to Clipboard Function
function copyToClipboard(text) {
    navigator.clipboard.writeText(text).then(() => {
        // Show feedback
        const feedback = document.createElement('div');
        feedback.textContent = '¡Copiado!';
        feedback.style.cssText = `
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%);
            background: var(--accent-success);
            color: var(--bg-primary);
            padding: 1rem 2rem;
            border-radius: 8px;
            font-weight: 600;
            z-index: 9999;
            animation: fadeInUp 0.3s ease-out;
        `;
        document.body.appendChild(feedback);
        setTimeout(() => feedback.remove(), 2000);
    });
}

// Add Copy Buttons to Code Blocks
document.querySelectorAll('.code-block, .installer-command').forEach(block => {
    const button = document.createElement('button');
    button.innerHTML = '📋 Copiar';
    button.style.cssText = `
        position: absolute;
        top: 0.5rem;
        right: 0.5rem;
        background: var(--bg-tertiary);
        color: var(--text-primary);
        border: 1px solid rgba(136, 192, 208, 0.2);
        padding: 0.25rem 0.75rem;
        border-radius: 4px;
        cursor: pointer;
        font-size: 0.75rem;
        transition: all 0.3s ease;
    `;
    
    button.addEventListener('click', () => {
        const code = block.querySelector('code');
        if (code) {
            copyToClipboard(code.textContent);
        }
    });
    
    block.style.position = 'relative';
    block.appendChild(button);
});

// Animated Stats Counter
function animateCounter(element, target, duration = 2000) {
    const start = 0;
    const increment = target / (duration / 16);
    let current = start;
    
    const timer = setInterval(() => {
        current += increment;
        if (current >= target) {
            element.textContent = target;
            clearInterval(timer);
        } else {
            element.textContent = Math.floor(current);
        }
    }, 16);
}

// Observe hero stats
const statsObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
        if (entry.isIntersecting) {
            const statValue = entry.target.querySelector('.stat-value');
            if (statValue && !statValue.dataset.animated) {
                statValue.dataset.animated = 'true';
                // You can add counter animation here if needed
            }
        }
    });
}, { threshold: 0.5 });

document.querySelectorAll('.stat').forEach(stat => {
    statsObserver.observe(stat);
});

// Easter Egg: Konami Code
let konamiCode = [];
const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];

document.addEventListener('keydown', (e) => {
    konamiCode.push(e.key);
    konamiCode = konamiCode.slice(-10);
    
    if (konamiCode.join(',') === konamiSequence.join(',')) {
        // Activate easter egg
        document.body.style.animation = 'rainbow 2s infinite';
        setTimeout(() => {
            document.body.style.animation = '';
        }, 5000);
    }
});

// Add rainbow animation
const style = document.createElement('style');
style.textContent = `
    @keyframes rainbow {
        0% { filter: hue-rotate(0deg); }
        100% { filter: hue-rotate(360deg); }
    }
`;
document.head.appendChild(style);

// Performance Monitoring
if ('PerformanceObserver' in window) {
    const observer = new PerformanceObserver((list) => {
        for (const entry of list.getEntries()) {
            console.log(`Resource: ${entry.name} - Duration: ${entry.duration}ms`);
        }
    });
    observer.observe({ entryTypes: ['resource', 'navigation'] });
}

// Add hover effect to feature cards
document.querySelectorAll('.feature-card, .installer-card').forEach(card => {
    card.addEventListener('mouseenter', function() {
        this.style.transform = 'translateY(-8px)';
    });
    
    card.addEventListener('mouseleave', function() {
        this.style.transform = 'translateY(0)';
    });
});

console.log('%c🤖 madOS - AI-Orchestrated Arch Linux', 'font-size: 20px; font-weight: bold; color: #88c0d0;');
console.log('%cPowered by Claude Code', 'font-size: 14px; color: #81a1c1;');
console.log('%c\nVisit: https://github.com/madkoding/mad-os', 'color: #a3be8c;');

// Language Selector
document.addEventListener('DOMContentLoaded', () => {
    const langButtons = document.querySelectorAll('.lang-option');
    
    langButtons.forEach(button => {
        button.addEventListener('click', () => {
            const selectedLang = button.dataset.lang;
            i18n.setLanguage(selectedLang);
        });
    });
    
    // Update copy feedback text based on language
    const originalCopyFunction = copyToClipboard;
    window.copyToClipboard = function(text) {
        navigator.clipboard.writeText(text).then(() => {
            const copyText = i18n.currentLang === 'es' ? '¡Copiado!' : 'Copied!';
            const feedback = document.createElement('div');
            feedback.textContent = copyText;
            feedback.style.cssText = `
                position: fixed;
                top: 50%;
                left: 50%;
                transform: translate(-50%, -50%);
                background: var(--accent-success);
                color: var(--bg-primary);
                padding: 1rem 2rem;
                border-radius: 8px;
                font-weight: 600;
                z-index: 9999;
                animation: fadeInUp 0.3s ease-out;
            `;
            document.body.appendChild(feedback);
            setTimeout(() => feedback.remove(), 2000);
        });
    };
    
    // Update copy button text based on language
    function updateCopyButtons() {
        const copyText = i18n.currentLang === 'es' ? '📋 Copiar' : '📋 Copy';
        document.querySelectorAll('.code-block button, .installer-command button').forEach(button => {
            if (button.textContent.includes('📋')) {
                button.innerHTML = copyText;
            }
        });
    }
    
    // Override the i18n setLanguage to update copy buttons
    const originalSetLanguage = i18n.setLanguage.bind(i18n);
    i18n.setLanguage = function(lang) {
        originalSetLanguage(lang);
        updateCopyButtons();
    };
});

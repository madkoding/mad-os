// ============================================
// madOS — Site Scripts
// ============================================

(function () {
    'use strict';

    // Mobile Menu Toggle
    const mobileMenuToggle = document.querySelector('.mobile-menu-toggle');
    const navMenu = document.querySelector('.nav-menu');

    if (mobileMenuToggle) {
        mobileMenuToggle.addEventListener('click', () => {
            navMenu.classList.toggle('active');
            mobileMenuToggle.classList.toggle('active');
        });
    }

    // Close mobile menu on link click
    document.querySelectorAll('.nav-menu a[href^="#"]').forEach(link => {
        link.addEventListener('click', () => {
            if (navMenu.classList.contains('active')) {
                navMenu.classList.remove('active');
                mobileMenuToggle.classList.remove('active');
            }
        });
    });

    // Smooth Scroll for Navigation Links
    document.querySelectorAll('a[href^="#"]').forEach(anchor => {
        anchor.addEventListener('click', function (e) {
            e.preventDefault();
            const target = document.querySelector(this.getAttribute('href'));
            if (target) {
                const navHeight = document.querySelector('.navbar').offsetHeight;
                const targetPosition = target.getBoundingClientRect().top + window.pageYOffset - navHeight;
                window.scrollTo({
                    top: targetPosition,
                    behavior: 'smooth'
                });
            }
        });
    });

    // Navbar scroll effect
    const navbar = document.querySelector('.navbar');
    window.addEventListener('scroll', () => {
        if (window.pageYOffset > 50) {
            navbar.classList.add('scrolled');
        } else {
            navbar.classList.remove('scrolled');
        }
    }, { passive: true });

    // Intersection Observer — reveal animations
    const revealElements = document.querySelectorAll(
        '.feature-card, .spec-item, .app-group, .step, .preview-frame, .system-monitor, .download-card'
    );

    const revealObserver = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('visible');
                revealObserver.unobserve(entry.target);
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -40px 0px'
    });

    revealElements.forEach((el, i) => {
        el.classList.add('reveal');
        el.style.transitionDelay = `${Math.min(i % 6, 4) * 0.08}s`;
        revealObserver.observe(el);
    });

    // Copy to clipboard for code blocks
    document.querySelectorAll('.step-content code, .installer-command code').forEach(block => {
        block.style.cursor = 'pointer';
        block.setAttribute('title', 'Click to copy');

        block.addEventListener('click', () => {
            navigator.clipboard.writeText(block.textContent.trim()).then(() => {
                const originalText = block.textContent;
                const copyText = 'Copied!';
                block.textContent = copyText;
                block.style.color = 'var(--nord14)';
                setTimeout(() => {
                    block.textContent = originalText;
                    block.style.color = '';
                }, 1500);
            });
        });
    });

    // Console branding
    console.log('%cmadOS', 'font-size: 24px; font-weight: bold; color: #88c0d0;');
    console.log('%cAI-Orchestrated Arch Linux', 'font-size: 12px; color: #81a1c1;');
    console.log('%chttps://github.com/madkoding/mad-os', 'font-size: 11px; color: #a3be8c;');

    // Konami Easter Egg
    let konamiCode = [];
    const konamiSequence = ['ArrowUp', 'ArrowUp', 'ArrowDown', 'ArrowDown', 'ArrowLeft', 'ArrowRight', 'ArrowLeft', 'ArrowRight', 'b', 'a'];

    document.addEventListener('keydown', (e) => {
        konamiCode.push(e.key);
        konamiCode = konamiCode.slice(-10);

        if (konamiCode.join(',') === konamiSequence.join(',')) {
            document.body.style.animation = 'rainbow 2s infinite';
            setTimeout(() => {
                document.body.style.animation = '';
            }, 5000);
        }
    });

    const style = document.createElement('style');
    style.textContent = '@keyframes rainbow { 0% { filter: hue-rotate(0deg); } 100% { filter: hue-rotate(360deg); } }';
    document.head.appendChild(style);
})();

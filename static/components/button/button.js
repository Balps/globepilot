/* Button Component JavaScript */

class Button {
    constructor(element, options = {}) {
        this.element = element;
        this.options = { 
            ...this.defaults, 
            ...options 
        };
        
        this.init();
    }
    
    defaults = {
        rippleEffect: true,
        clickAnimation: true,
        loadingTimeout: null,
        analytics: true
    };
    
    init() {
        this.bindEvents();
        this.setupRippleEffect();
        this.setupAnalytics();
    }
    
    bindEvents() {
        // Click handler
        this.element.addEventListener('click', this.handleClick.bind(this));
        
        // Keyboard handler
        this.element.addEventListener('keydown', this.handleKeydown.bind(this));
        
        // Mouse events for animations
        this.element.addEventListener('mousedown', this.handleMouseDown.bind(this));
        this.element.addEventListener('mouseup', this.handleMouseUp.bind(this));
        this.element.addEventListener('mouseleave', this.handleMouseLeave.bind(this));
    }
    
    handleClick(event) {
        // Prevent click if button is disabled or loading
        if (this.isDisabled() || this.isLoading()) {
            event.preventDefault();
            event.stopPropagation();
            return false;
        }
        
        // Add click animation
        if (this.options.clickAnimation) {
            this.addClickAnimation();
        }
        
        // Track analytics
        if (this.options.analytics) {
            this.trackClick();
        }
        
        // Handle loading state if specified
        if (this.element.dataset.autoLoading === 'true') {
            this.setLoading(true);
        }
    }
    
    handleKeydown(event) {
        // Handle Enter and Space keys
        if (event.key === 'Enter' || event.key === ' ') {
            event.preventDefault();
            this.element.click();
        }
    }
    
    handleMouseDown(event) {
        if (this.isDisabled()) return;
        
        // Add pressed state
        this.element.classList.add('btn--pressed');
    }
    
    handleMouseUp(event) {
        // Remove pressed state
        this.element.classList.remove('btn--pressed');
    }
    
    handleMouseLeave(event) {
        // Remove pressed state when mouse leaves
        this.element.classList.remove('btn--pressed');
    }
    
    setupRippleEffect() {
        if (!this.options.rippleEffect) return;
        
        this.element.addEventListener('click', (event) => {
            if (this.isDisabled() || this.isLoading()) return;
            
            this.createRipple(event);
        });
    }
    
    createRipple(event) {
        const rect = this.element.getBoundingClientRect();
        const size = Math.max(rect.width, rect.height);
        const x = event.clientX - rect.left - size / 2;
        const y = event.clientY - rect.top - size / 2;
        
        const ripple = document.createElement('span');
        ripple.className = 'btn__ripple';
        ripple.style.cssText = `
            position: absolute;
            width: ${size}px;
            height: ${size}px;
            left: ${x}px;
            top: ${y}px;
            background: rgba(255, 255, 255, 0.3);
            border-radius: 50%;
            transform: scale(0);
            animation: ripple 0.6s ease-out;
            pointer-events: none;
            z-index: 1;
        `;
        
        // Ensure button has relative positioning
        if (getComputedStyle(this.element).position === 'static') {
            this.element.style.position = 'relative';
        }
        
        this.element.appendChild(ripple);
        
        // Remove ripple after animation
        setTimeout(() => {
            if (ripple.parentNode) {
                ripple.parentNode.removeChild(ripple);
            }
        }, 600);
    }
    
    addClickAnimation() {
        this.element.style.transform = 'scale(0.98)';
        
        setTimeout(() => {
            this.element.style.transform = '';
        }, 150);
    }
    
    setupAnalytics() {
        if (!this.options.analytics) return;
        
        // Set up data attributes for tracking
        if (!this.element.dataset.trackingLabel) {
            const text = this.element.querySelector('.btn__text')?.textContent?.trim();
            this.element.dataset.trackingLabel = text || 'button';
        }
    }
    
    trackClick() {
        const label = this.element.dataset.trackingLabel;
        const category = this.element.dataset.trackingCategory || 'UI';
        
        // Send to analytics (Google Analytics, custom analytics, etc.)
        if (typeof gtag !== 'undefined') {
            gtag('event', 'click', {
                event_category: category,
                event_label: label
            });
        }
        
        // Custom analytics tracking
        if (window.GlobePilotAnalytics) {
            window.GlobePilotAnalytics.track('button_click', {
                label: label,
                category: category,
                element: this.element
            });
        }
    }
    
    // Public API methods
    setLoading(loading) {
        if (loading) {
            this.element.classList.add('btn--loading');
            this.element.disabled = true;
            
            // Store original text
            const textElement = this.element.querySelector('.btn__text');
            if (textElement && !this.originalText) {
                this.originalText = textElement.textContent;
                textElement.textContent = this.element.dataset.loadingText || 'Loading...';
            }
        } else {
            this.element.classList.remove('btn--loading');
            this.element.disabled = false;
            
            // Restore original text
            const textElement = this.element.querySelector('.btn__text');
            if (textElement && this.originalText) {
                textElement.textContent = this.originalText;
                this.originalText = null;
            }
        }
        
        return this;
    }
    
    setDisabled(disabled) {
        this.element.disabled = disabled;
        return this;
    }
    
    setText(text) {
        const textElement = this.element.querySelector('.btn__text');
        if (textElement) {
            textElement.textContent = text;
        }
        return this;
    }
    
    setVariant(variant) {
        // Remove existing variant classes
        const classList = this.element.classList;
        const variantClasses = Array.from(classList).filter(cls => cls.startsWith('btn--'));
        variantClasses.forEach(cls => {
            if (cls.includes('primary') || cls.includes('secondary') || 
                cls.includes('ghost') || cls.includes('danger') || cls.includes('success')) {
                classList.remove(cls);
            }
        });
        
        // Add new variant
        classList.add(`btn--${variant}`);
        return this;
    }
    
    // Utility methods
    isDisabled() {
        return this.element.disabled || this.element.hasAttribute('disabled');
    }
    
    isLoading() {
        return this.element.classList.contains('btn--loading');
    }
    
    destroy() {
        // Remove all event listeners and clean up
        this.element.removeEventListener('click', this.handleClick);
        this.element.removeEventListener('keydown', this.handleKeydown);
        this.element.removeEventListener('mousedown', this.handleMouseDown);
        this.element.removeEventListener('mouseup', this.handleMouseUp);
        this.element.removeEventListener('mouseleave', this.handleMouseLeave);
        
        // Remove any added styles
        this.element.style.position = '';
        this.element.style.transform = '';
        
        // Remove ripples
        const ripples = this.element.querySelectorAll('.btn__ripple');
        ripples.forEach(ripple => ripple.remove());
    }
}

// CSS for ripple effect
const rippleCSS = `
@keyframes ripple {
    to {
        transform: scale(4);
        opacity: 0;
    }
}

.btn--pressed {
    transform: scale(0.98) !important;
}
`;

// Inject ripple CSS
if (!document.querySelector('#button-component-styles')) {
    const style = document.createElement('style');
    style.id = 'button-component-styles';
    style.textContent = rippleCSS;
    document.head.appendChild(style);
}

// Auto-initialize all button components
document.addEventListener('DOMContentLoaded', () => {
    const buttons = document.querySelectorAll('[data-component="button"]');
    buttons.forEach(button => {
        if (!button._buttonInstance) {
            button._buttonInstance = new Button(button);
        }
    });
});

// Initialize buttons added dynamically
const observer = new MutationObserver((mutations) => {
    mutations.forEach((mutation) => {
        mutation.addedNodes.forEach((node) => {
            if (node.nodeType === 1) { // Element node
                // Check if the node itself is a button component
                if (node.matches && node.matches('[data-component="button"]') && !node._buttonInstance) {
                    node._buttonInstance = new Button(node);
                }
                
                // Check for button components within the added node
                const buttons = node.querySelectorAll && node.querySelectorAll('[data-component="button"]');
                if (buttons) {
                    buttons.forEach(button => {
                        if (!button._buttonInstance) {
                            button._buttonInstance = new Button(button);
                        }
                    });
                }
            }
        });
    });
});

observer.observe(document.body, { childList: true, subtree: true });

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = Button;
} else if (typeof window !== 'undefined') {
    window.Button = Button;
} 
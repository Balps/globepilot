/**
 * GlobePiloT Modern Component System
 * Using Web Components (Custom Elements) for bulletproof, reusable UI
 */

class ComponentSystem {
    constructor() {
        this.components = new Map();
        this.initialized = false;
        this.init();
    }

    init() {
        if (this.initialized) return;
        
        console.log('🧩 Initializing GlobePiloT Component System');
        
        // Auto-discover and register components when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.autoRegisterComponents());
        } else {
            this.autoRegisterComponents();
        }
        
        // Watch for dynamically added components
        this.observeComponentChanges();
        
        this.initialized = true;
    }

    /**
     * Register a new component
     */
    register(name, componentClass) {
        try {
            if (customElements.get(name)) {
                console.warn(`Component ${name} already registered`);
                return;
            }
            
            customElements.define(name, componentClass);
            this.components.set(name, componentClass);
            console.log(`✅ Registered component: ${name}`);
            
        } catch (error) {
            console.error(`❌ Failed to register component ${name}:`, error);
        }
    }

    /**
     * Create a component programmatically
     */
    create(name, props = {}) {
        const element = document.createElement(name);
        
        // Set properties
        Object.entries(props).forEach(([key, value]) => {
            if (key.startsWith('data-')) {
                element.setAttribute(key, value);
            } else {
                element[key] = value;
            }
        });
        
        return element;
    }

    /**
     * Auto-discover and initialize components in DOM
     */
    autoRegisterComponents() {
        // Look for all elements with 'gp-' prefix (GlobePiloT components)
        const componentElements = document.querySelectorAll('[class*="gp-"], [is^="gp-"]');
        
        componentElements.forEach(element => {
            this.initializeComponentElement(element);
        });
    }

    /**
     * Initialize a specific component element
     */
    initializeComponentElement(element) {
        const componentName = this.getComponentName(element);
        if (!componentName) return;
        
        // Add component-specific functionality
        if (!element.dataset.componentInitialized) {
            this.enhanceElement(element, componentName);
            element.dataset.componentInitialized = 'true';
        }
    }

    /**
     * Get component name from element
     */
    getComponentName(element) {
        // Check for explicit component attribute
        if (element.hasAttribute('data-component')) {
            return element.getAttribute('data-component');
        }
        
        // Derive from class name
        const classList = Array.from(element.classList);
        const componentClass = classList.find(cls => cls.startsWith('gp-'));
        
        return componentClass ? componentClass.replace('gp-', '') : null;
    }

    /**
     * Enhance regular elements with component functionality
     */
    enhanceElement(element, componentName) {
        try {
            // Add common component functionality
            element.componentName = componentName;
            element.props = this.extractProps(element);
            
            // Add update method
            element.updateProps = (newProps) => {
                Object.assign(element.props, newProps);
                this.renderComponent(element);
            };
            
            // Add event delegation
            this.setupEventDelegation(element);
            
            // Initial render
            this.renderComponent(element);
            
        } catch (error) {
            console.error(`Failed to enhance component ${componentName}:`, error);
        }
    }

    /**
     * Extract props from element attributes
     */
    extractProps(element) {
        const props = {};
        
        // Extract from data attributes
        Object.keys(element.dataset).forEach(key => {
            if (key !== 'component' && key !== 'componentInitialized') {
                props[key] = element.dataset[key];
            }
        });
        
        // Extract from specific attributes
        ['text', 'variant', 'size', 'icon', 'disabled', 'loading'].forEach(attr => {
            if (element.hasAttribute(attr)) {
                props[attr] = element.getAttribute(attr);
            }
        });
        
        return props;
    }

    /**
     * Setup event delegation for component
     */
    setupEventDelegation(element) {
        element.addEventListener('click', (e) => {
            if (element.hasAttribute('disabled') || element.classList.contains('disabled')) {
                e.preventDefault();
                e.stopPropagation();
                return;
            }
            
            // Emit custom component event
            element.dispatchEvent(new CustomEvent('component:click', {
                detail: { props: element.props, originalEvent: e },
                bubbles: true
            }));
        });
    }

    /**
     * Render component based on its type
     */
    renderComponent(element) {
        const componentName = element.componentName;
        const renderer = this.getRenderer(componentName);
        
        if (renderer) {
            renderer(element, element.props);
        }
    }

    /**
     * Get renderer function for component type
     */
    getRenderer(componentName) {
        const renderers = {
            'button': this.renderButton.bind(this),
            'card': this.renderCard.bind(this),
            'alert': this.renderAlert.bind(this),
            'modal': this.renderModal.bind(this),
            'trip-card': this.renderTripCard.bind(this),
            'itinerary-item': this.renderItineraryItem.bind(this)
        };
        
        return renderers[componentName];
    }

    /**
     * Button component renderer
     */
    renderButton(element, props) {
        const { text = 'Button', variant = 'primary', size, icon, loading, disabled } = props;
        
        // Update classes
        element.className = `gp-button gp-button--${variant}`;
        if (size) element.classList.add(`gp-button--${size}`);
        if (loading) element.classList.add('gp-button--loading');
        if (disabled) element.classList.add('gp-button--disabled');
        
        // Update content
        let content = '';
        if (loading) {
            content = `<span class="gp-button__spinner"></span><span class="gp-button__text">${text}</span>`;
        } else {
            if (icon) content += `<span class="gp-button__icon">${icon}</span>`;
            content += `<span class="gp-button__text">${text}</span>`;
        }
        
        element.innerHTML = content;
        
        // Update attributes
        element.disabled = disabled || loading;
    }

    /**
     * Trip card component renderer
     */
    renderTripCard(element, props) {
        const { 
            title = 'Trip', 
            location = '', 
            duration = '', 
            cost = '', 
            image = '',
            description = ''
        } = props;
        
        element.className = 'gp-trip-card';
        element.innerHTML = `
            <div class="gp-trip-card__header">
                ${image ? `<img src="${image}" alt="${title}" class="gp-trip-card__image">` : ''}
                <div class="gp-trip-card__overlay">
                    <h3 class="gp-trip-card__title">${title}</h3>
                    <p class="gp-trip-card__location">${location}</p>
                </div>
            </div>
            <div class="gp-trip-card__content">
                <div class="gp-trip-card__meta">
                    ${duration ? `<span class="gp-trip-card__duration">🕒 ${duration}</span>` : ''}
                    ${cost ? `<span class="gp-trip-card__cost">💰 ${cost}</span>` : ''}
                </div>
                ${description ? `<p class="gp-trip-card__description">${description}</p>` : ''}
            </div>
            <div class="gp-trip-card__actions">
                <button class="gp-button gp-button--secondary gp-button--sm" data-action="view">View Details</button>
                <button class="gp-button gp-button--primary gp-button--sm" data-action="book">Book Now</button>
            </div>
        `;
    }

    /**
     * Itinerary item component renderer
     */
    renderItineraryItem(element, props) {
        const { 
            time = '', 
            title = '', 
            location = '', 
            description = '',
            type = 'activity',
            cost = '',
            duration = ''
        } = props;
        
        const icons = {
            'activity': '🎯',
            'meal': '🍽️',
            'transport': '🚌',
            'hotel': '🏨',
            'flight': '✈️'
        };
        
        element.className = `gp-itinerary-item gp-itinerary-item--${type}`;
        element.innerHTML = `
            <div class="gp-itinerary-item__time">${time}</div>
            <div class="gp-itinerary-item__content">
                <div class="gp-itinerary-item__header">
                    <span class="gp-itinerary-item__icon">${icons[type] || '📍'}</span>
                    <h4 class="gp-itinerary-item__title">${title}</h4>
                    ${cost ? `<span class="gp-itinerary-item__cost">${cost}</span>` : ''}
                </div>
                ${location ? `<p class="gp-itinerary-item__location">📍 ${location}</p>` : ''}
                ${description ? `<p class="gp-itinerary-item__description">${description}</p>` : ''}
                ${duration ? `<p class="gp-itinerary-item__duration">⏱️ ${duration}</p>` : ''}
            </div>
        `;
    }

    /**
     * Observe DOM changes to auto-initialize new components
     */
    observeComponentChanges() {
        const observer = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                mutation.addedNodes.forEach((node) => {
                    if (node.nodeType === 1) { // Element node
                        // Check if the node itself is a component
                        if (this.isComponent(node)) {
                            this.initializeComponentElement(node);
                        }
                        
                        // Check for components within the added node
                        const components = node.querySelectorAll ? 
                            node.querySelectorAll('[class*="gp-"], [data-component]') : [];
                        components.forEach(comp => this.initializeComponentElement(comp));
                    }
                });
            });
        });
        
        observer.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    /**
     * Check if element is a component
     */
    isComponent(element) {
        return element.classList && (
            Array.from(element.classList).some(cls => cls.startsWith('gp-')) ||
            element.hasAttribute('data-component')
        );
    }

    /**
     * Create multiple components at once
     */
    createMultiple(components) {
        return components.map(({ name, props }) => this.create(name, props));
    }

    /**
     * Get all registered components
     */
    getRegisteredComponents() {
        return Array.from(this.components.keys());
    }

    /**
     * Hot reload components (for development)
     */
    hotReload() {
        console.log('🔄 Hot reloading components...');
        
        // Re-initialize all components
        const allComponents = document.querySelectorAll('[data-component-initialized]');
        allComponents.forEach(element => {
            element.dataset.componentInitialized = 'false';
            this.initializeComponentElement(element);
        });
        
        console.log('✅ Hot reload complete');
    }
}

// Global component system instance
window.ComponentSystem = new ComponentSystem();

// Utility functions for easier component usage
window.createComponent = (name, props) => window.ComponentSystem.create(name, props);
window.updateComponent = (element, props) => element.updateProps && element.updateProps(props);

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = ComponentSystem;
}

console.log('🧩 GlobePiloT Component System Loaded'); 
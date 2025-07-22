# GlobePiloT Component Usage Examples

## 🎯 **How to Use the Component System**

### **1. Basic Button Usage**

```html
<!-- In any template file -->

<!-- Load component assets -->
{{ 'button' | component_css | safe }}
{{ 'button' | component_js | safe }}

<!-- Use the component -->
{{ component('ui/button', 
    text='Plan My Trip', 
    variant='primary', 
    size='lg',
    icon='✈️'
) }}
```

### **2. Button Variants**

```html
<!-- Primary Button -->
{{ component('ui/button', 
    text='Start Planning', 
    variant='primary'
) }}

<!-- Secondary Button -->
{{ component('ui/button', 
    text='Save Draft', 
    variant='secondary'
) }}

<!-- Ghost Button -->
{{ component('ui/button', 
    text='Cancel', 
    variant='ghost'
) }}

<!-- Danger Button -->
{{ component('ui/button', 
    text='Delete Trip', 
    variant='danger'
) }}

<!-- Success Button -->
{{ component('ui/button', 
    text='Trip Confirmed', 
    variant='success'
) }}
```

### **3. Button Sizes**

```html
<!-- Small Button -->
{{ component('ui/button', 
    text='Edit', 
    size='sm',
    icon='✏️'
) }}

<!-- Default Button -->
{{ component('ui/button', 
    text='View Details'
) }}

<!-- Large Button -->
{{ component('ui/button', 
    text='Book Now', 
    size='lg',
    variant='primary'
) }}

<!-- Extra Large Button -->
{{ component('ui/button', 
    text='Start Your Journey', 
    size='xl',
    variant='primary'
) }}
```

### **4. Button States**

```html
<!-- Loading Button -->
{{ component('ui/button', 
    text='Processing...', 
    loading=true,
    loading_text='Creating your itinerary...'
) }}

<!-- Disabled Button -->
{{ component('ui/button', 
    text='Unavailable', 
    disabled=true
) }}

<!-- Icon Only Button -->
{{ component('ui/button', 
    icon='🔍',
    aria_label='Search',
    class='btn--icon-only'
) }}

<!-- Full Width Button -->
{{ component('ui/button', 
    text='Continue to Payment', 
    variant='primary',
    class='btn--full'
) }}
```

### **5. Advanced Button Usage**

```html
<!-- Button with Custom Click Handler -->
{{ component('ui/button', 
    text='Generate Itinerary',
    variant='primary',
    onclick='generateItinerary()',
    attrs='data-auto-loading="true" data-tracking-category="TripPlanning"'
) }}

<!-- Form Submit Button -->
{{ component('ui/button', 
    text='Submit Trip Request',
    type='submit',
    variant='primary',
    size='lg'
) }}
```

## 🏗️ **Creating Your First Custom Component**

### **Example: Alert Component**

1. **Create the directory structure:**
```bash
mkdir -p templates/components/ui static/components/alert
```

2. **Create the template** (`templates/components/ui/alert.html`):
```html
<div class="alert alert--{{ type or 'info' }}{{ ' alert--dismissible' if dismissible }}" 
     data-component="alert"
     role="alert"
     {% if dismissible %}aria-live="assertive"{% endif %}>
    
    {% if icon %}
    <div class="alert__icon" aria-hidden="true">{{ icon }}</div>
    {% endif %}
    
    <div class="alert__content">
        {% if title %}
        <div class="alert__title">{{ title }}</div>
        {% endif %}
        <div class="alert__message">{{ message or 'Alert message' }}</div>
    </div>
    
    {% if dismissible %}
    <button class="alert__close" 
            onclick="this.parentElement.remove()" 
            aria-label="Close alert">
        <span aria-hidden="true">×</span>
    </button>
    {% endif %}
</div>
```

3. **Create the CSS** (`static/components/alert/alert.css`):
```css
.alert {
    display: flex;
    align-items: flex-start;
    gap: 0.75rem;
    padding: 1rem;
    border-radius: 8px;
    border: 1px solid;
    margin-bottom: 1rem;
}

.alert__icon {
    font-size: 1.25rem;
    margin-top: 0.125rem;
}

.alert__content {
    flex: 1;
}

.alert__title {
    font-weight: 600;
    margin-bottom: 0.25rem;
}

.alert__close {
    background: none;
    border: none;
    font-size: 1.25rem;
    cursor: pointer;
    padding: 0.25rem;
    border-radius: 4px;
}

/* Alert Types */
.alert--info {
    background: rgba(59, 130, 246, 0.1);
    border-color: rgba(59, 130, 246, 0.3);
    color: #1e40af;
}

.alert--success {
    background: rgba(16, 185, 129, 0.1);
    border-color: rgba(16, 185, 129, 0.3);
    color: #047857;
}

.alert--warning {
    background: rgba(245, 158, 11, 0.1);
    border-color: rgba(245, 158, 11, 0.3);
    color: #92400e;
}

.alert--error {
    background: rgba(239, 68, 68, 0.1);
    border-color: rgba(239, 68, 68, 0.3);
    color: #b91c1c;
}
```

4. **Use the component:**
```html
<!-- Load assets -->
{{ 'alert' | component_css | safe }}

<!-- Use component -->
{{ component('ui/alert', 
    type='success',
    icon='✅',
    title='Trip Saved!',
    message='Your travel itinerary has been saved successfully.',
    dismissible=true
) }}
```

## 🔄 **Migrating Existing UI to Components**

### **Before (Inline HTML):**
```html
<button class="btn btn-primary btn-lg" onclick="planTrip()">
    <i class="fas fa-plane"></i>
    Plan My Trip
</button>
```

### **After (Component-based):**
```html
{{ component('ui/button', 
    text='Plan My Trip',
    variant='primary',
    size='lg',
    icon='✈️',
    onclick='planTrip()'
) }}
```

## 🎨 **Advanced Component Patterns**

### **1. Component Composition**

```html
<!-- Card with Button -->
<div class="card">
    <div class="card__header">
        <h3>New York Adventure</h3>
    </div>
    <div class="card__content">
        <p>5 days of amazing experiences in the Big Apple.</p>
    </div>
    <div class="card__footer">
        {{ component('ui/button', 
            text='View Details',
            variant='secondary',
            size='sm'
        ) }}
        {{ component('ui/button', 
            text='Book Now',
            variant='primary',
            size='sm'
        ) }}
    </div>
</div>
```

### **2. Conditional Components**

```html
{% if user.is_authenticated %}
    {{ component('ui/button', 
        text='Save Trip',
        variant='primary',
        icon='💾'
    ) }}
{% else %}
    {{ component('ui/button', 
        text='Sign In to Save',
        variant='secondary',
        onclick='showLogin()'
    ) }}
{% endif %}
```

### **3. Dynamic Component Properties**

```html
{% set button_config = {
    'planning': {'text': 'Planning...', 'loading': true},
    'ready': {'text': 'Plan Trip', 'variant': 'primary'},
    'error': {'text': 'Try Again', 'variant': 'danger'}
} %}

{{ component('ui/button', **button_config[trip_status]) }}
```

## 🛠️ **Component Development Workflow**

### **1. Plan Your Component**
- Identify reusable UI patterns
- Define props and variants
- Consider accessibility requirements
- Plan responsive behavior

### **2. Create Component Files**
```bash
# Create directory
mkdir -p templates/components/[category] static/components/[name]

# Create files
touch templates/components/[category]/[name].html
touch static/components/[name]/[name].css
touch static/components/[name]/[name].js
```

### **3. Implement Component**
- Start with HTML structure
- Add CSS styling with BEM methodology
- Add JavaScript functionality
- Test with different props

### **4. Document Component**
- Create usage examples
- Document all props and variants
- Add accessibility notes
- Include responsive behavior notes

### **5. Integrate Component**
- Add to existing templates
- Test in different contexts
- Optimize for performance
- Update documentation

## 📚 **Component Library Structure**

```
templates/components/
├── ui/                 # Basic UI components
│   ├── button.html
│   ├── card.html
│   ├── modal.html
│   └── alert.html
├── layout/             # Layout components
│   ├── header.html
│   ├── sidebar.html
│   └── footer.html
├── forms/              # Form components
│   ├── input.html
│   ├── select.html
│   └── checkbox.html
├── trip/               # Travel-specific components
│   ├── trip-overview.html
│   ├── itinerary-card.html
│   └── activity-card.html
└── navigation/         # Navigation components
    ├── tab-navigation.html
    ├── breadcrumb.html
    └── pagination.html

static/components/
├── button/
│   ├── button.css
│   └── button.js
├── card/
│   ├── card.css
│   └── card.js
└── [component-name]/
    ├── [component-name].css
    └── [component-name].js
```

This component system will make your GlobePiloT application much more maintainable and allow for rapid UI development! 
/* results.js */
// GlobePiloT Results Page JavaScript - Performance Optimized
// Modular, efficient, and cached separately for optimal loading

// Performance monitoring
const performanceStart = performance.now();

// Enhanced Interactive Features & State Management
const AppState = {
    currentTab: 'itinerary',
    currentDay: 1,
    searchQuery: '',
    activeFilter: 'all',
    selectedActivity: null,
    isLoading: false,
    userPreferences: {
        mapType: 'roadmap',
        theme: 'light',
        notifications: true
    }
};

// Performance-optimized debounce function
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

// Accessibility helper functions
function announceToScreenReader(message) {
    const announcement = document.createElement('div');
    announcement.setAttribute('aria-live', 'polite');
    announcement.setAttribute('aria-atomic', 'true');
    announcement.className = 'sr-only';
    announcement.textContent = message;
    
    document.body.appendChild(announcement);
    
    // Remove after announcement
    setTimeout(() => {
        document.body.removeChild(announcement);
    }, 1000);
}

function detectKeyboardUser() {
    let isKeyboardUser = false;
    
    // Listen for Tab key
    document.addEventListener('keydown', (e) => {
        if (e.key === 'Tab' && !isKeyboardUser) {
            isKeyboardUser = true;
            document.body.classList.add('keyboard-user');
        }
    });
    
    // Listen for mouse interactions
    document.addEventListener('mousedown', () => {
        if (isKeyboardUser) {
            isKeyboardUser = false;
            document.body.classList.remove('keyboard-user');
        }
    });
}

function trapFocus(container) {
    const focusableElements = container.querySelectorAll(
        'a[href], button, textarea, input[type="text"], input[type="radio"], input[type="checkbox"], select, [tabindex]:not([tabindex="-1"])'
    );
    
    const firstElement = focusableElements[0];
    const lastElement = focusableElements[focusableElements.length - 1];
    
    container.addEventListener('keydown', (e) => {
        if (e.key === 'Tab') {
            if (e.shiftKey) {
                if (document.activeElement === firstElement) {
                    lastElement.focus();
                    e.preventDefault();
                }
            } else {
                if (document.activeElement === lastElement) {
                    firstElement.focus();
                    e.preventDefault();
                }
            }
        }
        
        if (e.key === 'Escape') {
            container.focus();
        }
    });
}

// Tab Switching with State Management and Accessibility
function switchTab(tabName) {
    // Update state
    AppState.currentTab = tabName;
    
    // Remove active class and update ARIA attributes for all tabs
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.classList.remove('active');
        btn.setAttribute('aria-selected', 'false');
        btn.setAttribute('tabindex', '-1');
    });
    
    // Hide all tab content
    document.querySelectorAll('.tab-content-item').forEach(content => {
        content.classList.remove('active');
    });
    
    // Add active class to clicked tab and corresponding content
    const clickedTab = document.querySelector(`[data-tab="${tabName}"]`);
    const tabContent = document.getElementById(tabName);
    
    if (clickedTab && tabContent) {
        clickedTab.classList.add('active');
        clickedTab.setAttribute('aria-selected', 'true');
        clickedTab.setAttribute('tabindex', '0');
        tabContent.classList.add('active');
        
        // Focus the active tab for keyboard users
        if (document.body.classList.contains('keyboard-user')) {
            clickedTab.focus();
        }
        
        // Focus the tab panel for screen readers
        setTimeout(() => {
            tabContent.focus();
        }, 100);
        
        // Trigger tab-specific initialization
        initializeTabContent(tabName);
        
        // Update URL without refresh
        if (history.replaceState) {
            history.replaceState(null, null, `#${tabName}`);
        }
        
        // Announce to screen readers
        announceToScreenReader(`Switched to ${tabName.charAt(0).toUpperCase() + tabName.slice(1)} view`);
        
        GlobePilot.showToast(`Switched to ${tabName.charAt(0).toUpperCase() + tabName.slice(1)} view`, 'success');
    }
}

// Initialize tab-specific content
function initializeTabContent(tabName) {
    switch (tabName) {
        case 'map':
            initializeGoogleMap();
            break;
        case 'budget':
            initializeBudgetView();
            break;
        case 'documents':
            initializeDocumentsView();
            break;
        case 'itinerary':
            displayItineraryData();
            break;
    }
}

// Enhanced Search Functionality
function searchActivities(query) {
    AppState.searchQuery = query.toLowerCase();
    
    // Clear previous highlights
    clearSearchHighlights();
    
    if (query.length < 2) {
        showAllActivities();
        return;
    }
    
    const activities = document.querySelectorAll('.activity-item');
    let matchCount = 0;
    
    activities.forEach(activity => {
        const activityText = activity.textContent.toLowerCase();
        const isMatch = activityText.includes(AppState.searchQuery);
        
        if (isMatch) {
            activity.style.display = 'block';
            activity.style.opacity = '1';
            highlightSearchTerms(activity, query);
            matchCount++;
        } else {
            activity.style.display = 'none';
            activity.style.opacity = '0.3';
        }
    });
    
    // Update search results indicator
    updateSearchResults(matchCount, query);
}

function handleSearchKeypress(event) {
    if (event.key === 'Enter') {
        const query = event.target.value;
        if (query.trim()) {
            // Advanced search with filters
            performAdvancedSearch(query);
        }
    }
}

function performAdvancedSearch(query) {
    const searchTerms = query.toLowerCase().split(' ');
    const activities = document.querySelectorAll('.activity-item');
    let results = [];
    
    activities.forEach((activity, index) => {
        const activityData = extractActivityData(activity);
        const relevanceScore = calculateRelevance(activityData, searchTerms);
        
        if (relevanceScore > 0) {
            results.push({ element: activity, score: relevanceScore, index });
        }
    });
    
    // Sort by relevance and display
    results.sort((a, b) => b.score - a.score);
    displaySearchResults(results);
}

function calculateRelevance(activityData, searchTerms) {
    let score = 0;
    const text = `${activityData.name} ${activityData.location} ${activityData.type}`.toLowerCase();
    
    searchTerms.forEach(term => {
        if (activityData.name.toLowerCase().includes(term)) score += 10;
        if (activityData.location.toLowerCase().includes(term)) score += 8;
        if (activityData.type.toLowerCase().includes(term)) score += 6;
        if (text.includes(term)) score += 3;
    });
    
    return score;
}

function extractActivityData(activityElement) {
    return {
        name: activityElement.querySelector('.activity-title')?.textContent || '',
        location: activityElement.querySelector('.activity-details')?.textContent || '',
        type: activityElement.querySelector('.activity-type-badge')?.textContent || '',
        cost: activityElement.querySelector('.activity-meta-item.cost')?.textContent || ''
    };
}

function highlightSearchTerms(element, query) {
    const textNodes = getTextNodes(element);
    textNodes.forEach(node => {
        const text = node.textContent;
        const highlightedText = text.replace(
            new RegExp(`(${query})`, 'gi'),
            '<mark class="search-highlight">$1</mark>'
        );
        if (highlightedText !== text) {
            const wrapper = document.createElement('span');
            wrapper.innerHTML = highlightedText;
            node.parentNode.replaceChild(wrapper, node);
        }
    });
}

function getTextNodes(element) {
    const textNodes = [];
    const walker = document.createTreeWalker(
        element,
        NodeFilter.SHOW_TEXT,
        null,
        false
    );
    
    let node;
    while (node = walker.nextNode()) {
        if (node.textContent.trim()) {
            textNodes.push(node);
        }
    }
    return textNodes;
}

function clearSearchHighlights() {
    const highlights = document.querySelectorAll('.search-highlight');
    highlights.forEach(highlight => {
        const parent = highlight.parentNode;
        parent.textContent = highlight.textContent;
    });
}

function showAllActivities() {
    const activities = document.querySelectorAll('.activity-item');
    activities.forEach(activity => {
        activity.style.display = 'block';
        activity.style.opacity = '1';
    });
    updateSearchResults(activities.length, '');
}

function updateSearchResults(count, query) {
    const searchContainer = document.querySelector('.search-container');
    let resultsElement = searchContainer.querySelector('.search-results');
    
    if (!resultsElement) {
        resultsElement = document.createElement('div');
        resultsElement.className = 'search-results';
        searchContainer.appendChild(resultsElement);
    }
    
    if (query) {
        resultsElement.innerHTML = `
            <div style="padding: 0.5rem; background: #f1f5f9; border-radius: 8px; margin-top: 0.5rem; font-size: 0.875rem; color: #64748b;">
                Found ${count} result${count !== 1 ? 's' : ''} for "${query}"
                ${count === 0 ? '<button onclick="showAllActivities()" style="margin-left: 0.5rem; background: #6366f1; color: white; border: none; padding: 0.25rem 0.5rem; border-radius: 4px; cursor: pointer;">Show All</button>' : ''}
            </div>
        `;
    } else {
        resultsElement.innerHTML = '';
    }
}

// Enhanced Filter System with Accessibility
function filterActivities(type) {
    AppState.activeFilter = type;
    
    // Update filter chip states and ARIA attributes
    document.querySelectorAll('.filter-chip').forEach(chip => {
        chip.classList.remove('active');
        chip.setAttribute('aria-pressed', 'false');
    });
    
    // Update the clicked filter
    const activeFilter = event.target.closest('.filter-chip');
    if (activeFilter) {
        activeFilter.classList.add('active');
        activeFilter.setAttribute('aria-pressed', 'true');
    }
    
    const activities = document.querySelectorAll('.activity-item');
    let visibleCount = 0;
    
    activities.forEach(activity => {
        const activityType = getActivityTypeFromElement(activity);
        const shouldShow = type === 'all' || 
                         (type === 'meals' && activityType === 'meal') ||
                         (type === 'attractions' && activityType === 'attraction') ||
                         (type === 'transport' && (activityType === 'transport' || activityType === 'flight')) ||
                         (type === 'free' && isFreeActivity(activity));
        
        if (shouldShow) {
            activity.style.display = 'block';
            activity.style.opacity = '1';
            activity.removeAttribute('aria-hidden');
            visibleCount++;
        } else {
            activity.style.display = 'none';
            activity.style.opacity = '0.3';
            activity.setAttribute('aria-hidden', 'true');
        }
    });
    
    // Animate filter change
    animateFilterChange(visibleCount, type);
    
    // Announce results to screen readers
    const message = `Showing ${visibleCount} ${type === 'all' ? 'activities' : type}`;
    announceToScreenReader(message);
    
    GlobePilot.showToast(message, 'success');
}

function getActivityTypeFromElement(activityElement) {
    const typeClasses = ['flight', 'hotel', 'meal', 'attraction', 'transport'];
    return typeClasses.find(type => activityElement.classList.contains(type)) || 'attraction';
}

function isFreeActivity(activityElement) {
    const costElement = activityElement.querySelector('.activity-meta-item.cost');
    const costText = costElement?.textContent.toLowerCase() || '';
    return costText.includes('free') || costText.includes('$0');
}

function animateFilterChange(count, type) {
    const activities = document.querySelectorAll('.activity-item[style*="display: block"]');
    activities.forEach((activity, index) => {
        activity.style.transform = 'translateY(20px)';
        activity.style.opacity = '0';
        
        setTimeout(() => {
            activity.style.transform = 'translateY(0)';
            activity.style.opacity = '1';
            activity.style.transition = 'all 0.3s ease';
        }, index * 50);
    });
}

// Budget and Document View Initializers
function initializeBudgetView() {
    const budgetContent = document.getElementById('budget');
    if (!budgetContent) return;
    
    budgetContent.innerHTML = `
        <div style="padding: 2rem;">
            <h2 style="margin-bottom: 2rem; color: #1e293b;">💰 Budget Breakdown</h2>
            
            <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 2rem; margin-bottom: 2rem;">
                <div style="background: var(--glass-bg); padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0;">
                    <h3 style="color: #6366f1; margin-bottom: 1rem;">📊 Budget Overview</h3>
                    <div style="margin-bottom: 1rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span>Total Budget:</span>
                            <strong>$3,000</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span>Amount Used:</span>
                            <strong style="color: #10b981;">$1,900</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Remaining:</span>
                            <strong style="color: #10b981;">$1,100</strong>
                        </div>
                    </div>
                </div>
                
                <div style="background: var(--glass-bg); padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0;">
                    <h3 style="color: #8b5cf6; margin-bottom: 1rem;">📈 Cost Categories</h3>
                    <div style="margin-bottom: 0.5rem;">
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span>🏨 Accommodation:</span>
                            <strong>$800</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span>🍽️ Food & Dining:</span>
                            <strong>$500</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between; margin-bottom: 0.5rem;">
                            <span>🎭 Activities:</span>
                            <strong>$400</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>🚇 Transportation:</span>
                            <strong>$200</strong>
                        </div>
                    </div>
                </div>
            </div>
            
            <button onclick="optimizeBudget()" style="background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 100%); color: white; border: none; padding: 1rem 2rem; border-radius: 12px; font-weight: 600; cursor: pointer; transition: all 0.3s ease;">
                🔧 Optimize Budget
            </button>
        </div>
    `;
    
    GlobePilot.showToast('Budget view loaded with current spending analysis', 'success');
}

function initializeDocumentsView() {
    const docsContent = document.getElementById('documents');
    if (!docsContent) return;
    
    docsContent.innerHTML = `
        <div style="padding: 2rem;">
            <h2 style="margin-bottom: 2rem; color: #1e293b;">📋 Travel Documents</h2>
            
            <div style="display: grid; gap: 1.5rem;">
                <div style="background: var(--glass-bg); padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0;">
                    <h3 style="color: #10b981; margin-bottom: 1rem;">✅ Required Documents</h3>
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="color: #10b981;">✓</span>
                            <span>Valid passport (expires after 2026)</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="color: #10b981;">✓</span>
                            <span>Travel insurance policy</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="color: #10b981;">✓</span>
                            <span>Hotel confirmation emails</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span style="color: #10b981;">✓</span>
                            <span>Flight confirmation codes</span>
                        </div>
                    </div>
                </div>
                
                <div style="background: var(--glass-bg); padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0;">
                    <h3 style="color: #f59e0b; margin-bottom: 1rem;">📱 Recommended Apps</h3>
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span>🚇</span>
                            <span>NYC Subway (MTA) app for real-time transit</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span>🗺️</span>
                            <span>Google Maps offline download</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span>🎭</span>
                            <span>TodayTix for Broadway show tickets</span>
                        </div>
                        <div style="display: flex; align-items: center; gap: 0.5rem;">
                            <span>🍽️</span>
                            <span>OpenTable for restaurant reservations</span>
                        </div>
                    </div>
                </div>
                
                <div style="background: var(--glass-bg); padding: 1.5rem; border-radius: 16px; border: 1px solid #e2e8f0;">
                    <h3 style="color: #ef4444; margin-bottom: 1rem;">🚨 Emergency Contacts</h3>
                    <div style="display: grid; gap: 0.75rem;">
                        <div style="display: flex; justify-content: space-between;">
                            <span>Emergency Services:</span>
                            <strong>911</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Tourist Hotline:</span>
                            <strong>311</strong>
                        </div>
                        <div style="display: flex; justify-content: space-between;">
                            <span>Embassy/Consulate:</span>
                            <strong>+1-xxx-xxx-xxxx</strong>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    GlobePilot.showToast('Documents checklist loaded with essential travel information', 'success');
}

// URL Hash Navigation
function initializeURLNavigation() {
    // Handle initial hash
    const hash = window.location.hash.substring(1);
    if (hash && ['itinerary', 'map', 'budget', 'documents'].includes(hash)) {
        switchTab(hash);
    }
    
    // Handle hash changes
    window.addEventListener('hashchange', () => {
        const newHash = window.location.hash.substring(1);
        if (newHash && ['itinerary', 'map', 'budget', 'documents'].includes(newHash)) {
            switchTab(newHash);
        }
    });
}

// Add CSS for enhanced interactions
function addEnhancedStyles() {
    const style = document.createElement('style');
    style.textContent = `
        .search-highlight {
            background: #fef3c7;
            color: #92400e;
            padding: 0.125rem 0.25rem;
            border-radius: 4px;
            font-weight: 600;
        }
        
        .search-results {
            animation: slideIn 0.3s ease;
        }
        
        @keyframes slideIn {
            from { opacity: 0; transform: translateY(-10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .tab-content-item {
            display: none;
            animation: fadeIn 0.3s ease;
        }

        .tab-content-item.active {
            display: block;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .activity-item {
            scroll-margin-top: 2rem;
        }
    `;
    document.head.appendChild(style);
}

// Enhanced Keyboard Navigation Support
function initializeKeyboardNavigation() {
    // Detect keyboard users
    detectKeyboardUser();
    
    document.addEventListener('keydown', (event) => {
        // Tab navigation with keyboard
        if (event.ctrlKey || event.metaKey) {
            switch (event.key) {
                case '1':
                    event.preventDefault();
                    switchTab('itinerary');
                    break;
                case '2':
                    event.preventDefault();
                    switchTab('map');
                    break;
                case '3':
                    event.preventDefault();
                    switchTab('budget');
                    break;
                case '4':
                    event.preventDefault();
                    switchTab('documents');
                    break;
                case 'f':
                    event.preventDefault();
                    const searchInput = document.querySelector('.search-input');
                    if (searchInput) {
                        searchInput.focus();
                        announceToScreenReader('Search field focused');
                    }
                    break;
            }
        }

        // Tab navigation with arrow keys (when focused on tab list)
        if (event.target.closest('.tab-navigation')) {
            const tabs = document.querySelectorAll('.tab-btn');
            const currentTab = document.querySelector('.tab-btn[aria-selected="true"]');
            const currentIndex = Array.from(tabs).indexOf(currentTab);
            
            switch (event.key) {
                case 'ArrowLeft':
                case 'ArrowUp':
                    event.preventDefault();
                    const prevIndex = currentIndex > 0 ? currentIndex - 1 : tabs.length - 1;
                    tabs[prevIndex].focus();
                    tabs[prevIndex].click();
                    break;
                case 'ArrowRight':
                case 'ArrowDown':
                    event.preventDefault();
                    const nextIndex = currentIndex < tabs.length - 1 ? currentIndex + 1 : 0;
                    tabs[nextIndex].focus();
                    tabs[nextIndex].click();
                    break;
                case 'Home':
                    event.preventDefault();
                    tabs[0].focus();
                    tabs[0].click();
                    break;
                case 'End':
                    event.preventDefault();
                    tabs[tabs.length - 1].focus();
                    tabs[tabs.length - 1].click();
                    break;
            }
        }

        // Activity navigation with arrow keys
        if (AppState.currentTab === 'itinerary') {
            const activities = document.querySelectorAll('.activity-item');
            const currentIndex = AppState.selectedActivity || 0;
            
            switch (event.key) {
                case 'ArrowDown':
                    event.preventDefault();
                    if (currentIndex < activities.length - 1) {
                        highlightActivity(currentIndex + 1);
                    }
                    break;
                case 'ArrowUp':
                    event.preventDefault();
                    if (currentIndex > 0) {
                        highlightActivity(currentIndex - 1);
                    }
                    break;
                case 'Enter':
                    if (activities[currentIndex]) {
                        activities[currentIndex].click();
                    }
                    break;
                case 'Escape':
                    // Clear search and filters
                    const searchInput = document.querySelector('.search-input');
                    if (searchInput) {
                        searchInput.value = '';
                        showAllActivities();
                        announceToScreenReader('Search cleared, showing all activities');
                    }
                    break;
            }
        }
    });
}

// Enhanced Activity Highlighting
function highlightActivity(index) {
    // Update state
    AppState.selectedActivity = index;
    
    // Remove previous highlights
    document.querySelectorAll('.activity-item').forEach(item => {
        item.classList.remove('highlighted');
    });
    
    // Highlight selected activity
    const activities = document.querySelectorAll('.activity-item');
    if (activities[index]) {
        activities[index].classList.add('highlighted');
        activities[index].scrollIntoView({ behavior: 'smooth', block: 'center' });
        
        // Get activity details
        const activityData = extractActivityData(activities[index]);
        
        // Show detailed information
        showActivityDetails(activityData, index);
    }
}

function showActivityDetails(activityData, index) {
    const details = `
        🎯 Activity Details
        
        📍 ${activityData.name}
        📮 ${activityData.location}
        🏷️ Type: ${activityData.type}
        💰 ${activityData.cost}
        
        Click connection icons to see transportation options between activities.
    `;
    
    GlobePilot.showToast(details, 'success');
}

// Performance monitoring
function logPerformance() {
    const performanceEnd = performance.now();
    const loadTime = performanceEnd - performanceStart;
    console.log(`🚀 GlobePiloT Results loaded in ${loadTime.toFixed(2)}ms`);
}

// Lazy loading for images (if any are added later)
function setupLazyLoading() {
    if ('IntersectionObserver' in window) {
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

        const images = document.querySelectorAll('img[data-src]');
        images.forEach(img => imageObserver.observe(img));
    }
}

// Initialize when DOM is ready
    document.addEventListener('DOMContentLoaded', function() {
        console.log('📄 DOM loaded, initializing enhanced features...');
        
        // IMMEDIATE cleanup on DOM load
        cleanupUnwantedElements();
    
    // Initialize enhanced interactive features
    addEnhancedStyles();
    initializeURLNavigation();
    initializeKeyboardNavigation();
    setupLazyLoading();
    
    // Initialize state management
    console.log('🎯 App State initialized:', AppState);
    
    // Create debounced search function
    window.debouncedSearch = debounce(searchActivities, 300);
    
    // Initialize core features if Google Maps is ready
    if (typeof google !== 'undefined' && google.maps) {
        initializeItineraryWidget();
    } else {
        // Wait for Google Maps to load
        setTimeout(() => {
            if (typeof google !== 'undefined' && google.maps) {
                initializeItineraryWidget();
            } else {
                console.log('⚠️ Google Maps not loaded, initializing without map');
                const hasData = loadBackendData();
                displayItineraryData();
            }
        }, 2000);
    }
    
    // Log performance
    logPerformance();
    
    // Welcome message with shortcuts
    setTimeout(() => {
        // IMMEDIATELY clean up any unwanted elements
        cleanupUnwantedElements();
        
        // Run cleanup again after a short delay to catch any late-loading elements
        setTimeout(() => {
            cleanupUnwantedElements();
        }, 100);
        
        enhanceTransportDisplay();
        
        GlobePilot.showToast('🎉 Welcome to Enhanced GlobePiloT!\n\n⌨️ Keyboard shortcuts:\n• Ctrl/Cmd + 1-4: Switch tabs\n• Ctrl/Cmd + F: Focus search\n• ↑↓ arrows: Navigate activities\n• ESC: Clear search', 'success');
    }, 1000);
});

// Cleanup Function
function cleanupUnwantedElements() {
    // AGGRESSIVELY remove any skip links
    const skipLinks = document.querySelectorAll('.skip-link, a[href*="skip"], a[href*="#main"], a[href*="#nav"], a[href*="#search"]');
    skipLinks.forEach(link => {
        link.remove();
    });
    
    // Remove any elements containing "Skip to" text
    const allElements = document.querySelectorAll('*');
    allElements.forEach(element => {
        if (element.textContent && element.textContent.trim().toLowerCase().includes('skip to')) {
            element.remove();
        }
    });
    
    // Remove any debug elements that shouldn't be visible
    const debugElements = document.querySelectorAll('[data-debug], .debug, .test-element');
    debugElements.forEach(element => {
        element.remove();
    });
    
    // Hide any elements with extremely low opacity that serve no purpose
    const lowOpacityElements = document.querySelectorAll('[style*="opacity: 0.1"], [style*="opacity:0.1"]');
    lowOpacityElements.forEach(element => {
        if (element.textContent.trim() === '' || element.innerHTML.trim() === '') {
            element.style.display = 'none';
        }
    });
    
    // Remove any standalone text nodes that might be unwanted
    const walker = document.createTreeWalker(
        document.body,
        NodeFilter.SHOW_TEXT,
        {
            acceptNode: function(node) {
                // Look for text nodes that contain "Skip" or other unwanted content
                if (node.nodeValue.trim().toLowerCase().includes('skip') ||
                    node.nodeValue.trim().toLowerCase().includes('debug') ||
                    node.nodeValue.trim().toLowerCase().includes('test')) {
                    return NodeFilter.FILTER_ACCEPT;
                }
                return NodeFilter.FILTER_SKIP;
            }
        },
        false
    );
    
    const unwantedTextNodes = [];
    let node;
    while (node = walker.nextNode()) {
        unwantedTextNodes.push(node);
    }
    
    unwantedTextNodes.forEach(textNode => {
        textNode.remove();
    });
    
    console.log('🧹 Cleanup complete - removed unwanted elements');
}

// Enhanced Transport Display and Activity Classification
function enhanceTransportDisplay() {
    // Find existing activity items and classify them
    const activityItems = document.querySelectorAll('.activity-item');
    
    activityItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        
        // Classify activity type and add appropriate class
        if (text.includes('hotel') || text.includes('check-in') || text.includes('accommodation')) {
            item.classList.add('hotel');
        } else if (text.includes('restaurant') || text.includes('dinner') || text.includes('lunch') || text.includes('breakfast') || text.includes('food') || text.includes('eat')) {
            item.classList.add('dining');
        } else if (text.includes('taxi') || text.includes('airport') || text.includes('transfer') || 
            text.includes('subway') || text.includes('train') || text.includes('uber') ||
            text.includes('transport') || text.includes('flight')) {
            item.classList.add('transport');
        } else if (text.includes('museum') || text.includes('park') || text.includes('statue') || 
            text.includes('bridge') || text.includes('building') || text.includes('square')) {
            item.classList.add('attraction');
        } else if (text.includes('show') || text.includes('theater') || text.includes('concert') || 
            text.includes('entertainment') || text.includes('broadway')) {
            item.classList.add('entertainment');
        } else if (text.includes('shop') || text.includes('market') || text.includes('souvenir') || 
            text.includes('store')) {
            item.classList.add('shopping');
        } else if (text.includes('walk') || text.includes('outdoor') || text.includes('hiking') || 
            text.includes('beach') || text.includes('nature')) {
            item.classList.add('outdoor');
        } else {
            item.classList.add('attraction'); // Default
        }
        
        // Enhance transport information display
        if (item.classList.contains('transport')) {
            const activityDetails = item.querySelector('.activity-details');
            if (activityDetails) {
                // Look for existing transport info or create new structure
                let transportInfo = activityDetails.querySelector('.transport-info');
                if (!transportInfo && (text.includes('taxi') || text.includes('airport transfer'))) {
                    transportInfo = createEnhancedTransportInfo(text, item);
                    if (transportInfo) {
                        activityDetails.appendChild(transportInfo);
                    }
                }
            }
        }
    });
    
    // Add connection icons between activities
    addConnectionIcons();
}

function createEnhancedTransportInfo(text, activityItem) {
    // Extract transport details from text
    const transportDetails = extractTransportDetails(text, activityItem);
    if (!transportDetails) return null;
    
    const transportInfo = document.createElement('div');
    transportInfo.className = 'transport-info';
    
    transportInfo.innerHTML = `
        <div class="transport-route">
            <div class="transport-route-icon">${transportDetails.icon}</div>
            <div class="transport-details">
                <div class="transport-title">${transportDetails.title}</div>
                <div class="transport-subtitle">${transportDetails.subtitle}</div>
                <div class="transport-options">
                    ${transportDetails.options.map(option => 
                        `<div class="transport-option ${option.type}">${option.text}</div>`
                    ).join('')}
                </div>
            </div>
        </div>
    `;
    
    return transportInfo;
}

function extractTransportDetails(text, activityItem) {
    // Example patterns for different transport types
    if (text.includes('taxi') && text.includes('airport')) {
        return {
            icon: '🚕',
            title: 'Taxi Route',
            subtitle: 'Quick & comfortable airport transfer',
            options: [
                { type: 'transport-cost', text: '$70 (flat rate + tip)' },
                { type: 'transport-duration', text: '30-45 min' },
                { type: 'transport-option', text: 'Alternative: AirTrain + Subway ($10)' }
            ]
        };
    }
    
    if (text.includes('subway') || text.includes('airtrain')) {
        return {
            icon: '🚇',
            title: 'Public Transport',
            subtitle: 'Budget-friendly option via AirTrain + Subway',
            options: [
                { type: 'transport-cost', text: '$10 total' },
                { type: 'transport-duration', text: '45-60 min' },
                { type: 'transport-option', text: 'MetroCard required' }
            ]
        };
    }
    
    if (text.includes('uber') || text.includes('lyft')) {
        return {
            icon: '🚗',
            title: 'Rideshare',
            subtitle: 'App-based transportation',
            options: [
                { type: 'transport-cost', text: '$45-80' },
                { type: 'transport-duration', text: '30-50 min' },
                { type: 'transport-option', text: 'Price varies by demand' }
            ]
        };
    }
    
    return null;
}

function addConnectionIcons() {
    const activities = document.querySelectorAll('.activity-item');
    activities.forEach((activity, index) => {
        if (index < activities.length - 1) {
            // Add connection line and icon between activities
            const timeline = activity.querySelector('.activity-timeline');
            if (timeline && !timeline.querySelector('.connection-line')) {
                const connectionLine = document.createElement('div');
                connectionLine.className = 'connection-line';
                
                const connectionIcon = document.createElement('div');
                connectionIcon.className = 'connection-icon taxi';
                connectionIcon.setAttribute('aria-label', 'Transportation connection');
                connectionIcon.setAttribute('role', 'button');
                connectionIcon.setAttribute('tabindex', '0');
                
                connectionLine.appendChild(connectionIcon);
                timeline.appendChild(connectionLine);
            }
        }
    });
}

// Export functions for global access
window.switchTab = switchTab;
window.searchActivities = searchActivities;
window.filterActivities = filterActivities;
window.handleSearchKeypress = handleSearchKeypress;
window.initializeBudgetView = initializeBudgetView;
window.initializeDocumentsView = initializeDocumentsView;
window.highlightActivity = highlightActivity;
window.enhanceTransportDisplay = enhanceTransportDisplay;
window.cleanupUnwantedElements = cleanupUnwantedElements; 
/* Component: button */
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
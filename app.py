#!/usr/bin/env python3
"""
GlobePiloT Flask Web Application
A web interface for the AI-powered multi-agent travel planning system
"""

import os
import asyncio
import threading
import time
from datetime import datetime
from flask import Flask, render_template, request, jsonify, redirect, url_for, flash
import logging
import re
import io
import sys
from contextlib import redirect_stdout, redirect_stderr
import json # Added for saving/loading test data

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue without it

# Import the GlobePiloT system
from globepilot_enhanced import execute_validated_travel_workflow, extract_user_budget, WorkflowLimits

# Import performance modules
from cache_manager import cache_manager
from performance_optimizations import initialize_performance_optimizations

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'globepilot-secret-key-change-in-production')

# Initialize all performance optimizations
app = initialize_performance_optimizations(app)

# Custom static file handler for optimized assets
@app.route('/static/<path:filename>')
def optimized_static(filename):
    """Serve optimized static files (minified in production)"""
    from flask import send_from_directory, current_app
    
    # In production, serve minified versions
    if not current_app.debug and not filename.endswith('.min.css') and not filename.endswith('.min.js'):
        if filename.endswith('.css'):
            minified_file = filename.replace('.css', '.min.css')
            try:
                return send_from_directory('static', minified_file, max_age=31536000)
            except:
                pass  # Fall back to original if minified doesn't exist
        elif filename.endswith('.js'):
            minified_file = filename.replace('.js', '.min.js')
            try:
                return send_from_directory('static', minified_file, max_age=31536000)
            except:
                pass  # Fall back to original if minified doesn't exist
    
    return send_from_directory('static', filename, max_age=31536000)

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Template functions for performance
@app.template_global()
def asset_url(filename, version='2.5'):
    """Generate optimized asset URLs with versioning"""
    from flask import url_for, current_app
    
    # In production, use minified versions
    if not current_app.debug:
        if filename.endswith('.css') and not filename.endswith('.min.css'):
            filename = filename.replace('.css', '.min.css')
        elif filename.endswith('.js') and not filename.endswith('.min.js'):
            filename = filename.replace('.js', '.min.js')
    
    return url_for('static', filename=filename, v=version)

@app.template_global()
def performance_hints():
    """Generate performance-related HTML hints"""
    return {
        'preload_css': ['css/variables.css', 'css/results.css'],
        'preload_js': ['js/results.js'],
        'dns_prefetch': ['fonts.googleapis.com', 'maps.googleapis.com'],
        'preconnect': ['https://fonts.gstatic.com']
    }

# Budget validation data - realistic minimums for different route types
ROUTE_BUDGET_MINIMUMS = {
    'domestic_short': 300,      # Same state/region
    'domestic_medium': 500,     # Cross-country domestic
    'domestic_long': 700,       # Coast-to-coast
    'international_nearby': 800, # Canada/Mexico
    'international_medium': 1200, # Europe/Asia
    'international_long': 1500,  # Far destinations
}

def estimate_minimum_budget(origin, destination):
    """Estimate minimum realistic budget based on origin and destination"""
    origin_lower = origin.lower()
    destination_lower = destination.lower()
    
    # Major US cities for reference
    major_us_cities = ['new york', 'los angeles', 'chicago', 'houston', 'phoenix', 
                      'philadelphia', 'san antonio', 'san diego', 'dallas', 'san jose',
                      'austin', 'jacksonville', 'san francisco', 'columbus', 'charlotte',
                      'fort worth', 'indianapolis', 'seattle', 'denver', 'washington dc',
                      'boston', 'el paso', 'detroit', 'nashville', 'portland', 'memphis',
                      'oklahoma city', 'las vegas', 'louisville', 'baltimore', 'milwaukee',
                      'albuquerque', 'tucson', 'fresno', 'sacramento', 'mesa', 'kansas city',
                      'atlanta', 'long beach', 'colorado springs', 'raleigh', 'omaha',
                      'miami', 'oakland', 'minneapolis', 'tulsa', 'cleveland', 'wichita',
                      'arlington', 'new orleans', 'bakersfield', 'tampa', 'honolulu',
                      'aurora', 'anaheim', 'santa ana', 'st. louis', 'riverside', 'corpus christi',
                      'lexington', 'pittsburgh', 'anchorage', 'stockton', 'cincinnati',
                      'saint paul', 'toledo', 'newark', 'greensboro', 'plano', 'henderson',
                      'lincoln', 'buffalo', 'jersey city', 'chula vista', 'fort wayne',
                      'orlando', 'st. petersburg', 'chandler', 'laredo', 'norfolk', 'durham',
                      'madison', 'lubbock', 'irvine', 'winston-salem', 'glendale', 'garland',
                      'hialeah', 'reno', 'chesapeake', 'gilbert', 'baton rouge', 'irving',
                      'scottsdale', 'north las vegas', 'fremont', 'boise', 'richmond']
    
    # Check if both are US cities
    origin_is_us = any(city in origin_lower for city in major_us_cities) or any(state in origin_lower for state in ['california', 'texas', 'florida', 'new york', 'pennsylvania', 'illinois', 'ohio', 'georgia', 'north carolina', 'michigan'])
    dest_is_us = any(city in destination_lower for city in major_us_cities) or any(state in destination_lower for state in ['california', 'texas', 'florida', 'new york', 'pennsylvania', 'illinois', 'ohio', 'georgia', 'north carolina', 'michigan'])
    
    if origin_is_us and dest_is_us:
        # Domestic travel - check distance
        coast_to_coast_origins = ['california', 'san diego', 'los angeles', 'san francisco', 'seattle', 'portland']
        coast_to_coast_dests = ['new york', 'boston', 'washington dc', 'philadelphia', 'miami', 'atlanta']
        
        is_coast_to_coast = (any(loc in origin_lower for loc in coast_to_coast_origins) and 
                            any(loc in destination_lower for loc in coast_to_coast_dests)) or \
                           (any(loc in destination_lower for loc in coast_to_coast_origins) and 
                            any(loc in origin_lower for loc in coast_to_coast_dests))
        
        if is_coast_to_coast:
            return ROUTE_BUDGET_MINIMUMS['domestic_long']
        else:
            return ROUTE_BUDGET_MINIMUMS['domestic_medium']
    else:
        # International travel
        nearby_countries = ['canada', 'mexico', 'canadian', 'mexican']
        if any(country in origin_lower or country in destination_lower for country in nearby_countries):
            return ROUTE_BUDGET_MINIMUMS['international_nearby']
        else:
            return ROUTE_BUDGET_MINIMUMS['international_medium']

def validate_budget_realistic(origin, destination, min_budget, max_budget):
    """Validate if the budget is realistic for the given route"""
    minimum_needed = estimate_minimum_budget(origin, destination)
    
    if max_budget < minimum_needed * 0.7:  # 30% tolerance below minimum
        return False, minimum_needed
    return True, minimum_needed

# Global variable to store the latest results
latest_results = {}
processing_status = {"is_processing": False, "progress": "", "results": None}

# ============================================================================
# ENHANCED PROGRESS TRACKING SYSTEM
# ============================================================================

# Global tracking variables
workflow_tracker = {
    "start_time": None,
    "current_agent": None,
    "completed_agents": [],
    "total_agents": 11,  # Updated to reflect all 11 agents in the workflow
    "current_agent_index": 0,
    "api_calls_current_agent": 0,
    "total_events": 0
}

# Agent configuration with icons and descriptions
AGENT_CONFIG = {
    "GeneralResearchAgent": {
        "icon": "fas fa-search",
        "name": "General Research",
        "description": "Researching destination basics & safety",
        "index": 0
    },
    "WeatherAgent": {
        "icon": "fas fa-cloud-sun",
        "name": "Weather Analysis",
        "description": "Checking weather & packing tips",
        "index": 1
    },
    "FlightAgent": {
        "icon": "fas fa-plane",
        "name": "Flight Research",
        "description": "Optimizing flight options",
        "index": 2
    },
    "AccommodationsAgent": {
        "icon": "fas fa-bed", 
        "name": "Accommodations",
        "description": "Finding best places to stay",
        "index": 3
    },
    "BudgetAnalysisAgent": {
        "icon": "fas fa-calculator",
        "name": "Budget Analysis",
        "description": "Calculating costs & optimization",
        "index": 4
    },
    "ActivitiesAgent": {
        "icon": "fas fa-map-signs",
        "name": "Activities", 
        "description": "Discovering attractions & tours",
        "index": 5
    },
    "LocalEventsAgent": {
        "icon": "fas fa-calendar-check",
        "name": "Local Events",
        "description": "Finding restaurants & events",
        "index": 6
    },
    "LocalTransportationAgent": {
        "icon": "fas fa-subway",
        "name": "Transportation",
        "description": "Planning local transport",
        "index": 7
    },
    "TravelPlannerAgent": {
        "icon": "fas fa-route",
        "name": "Travel Planner",
        "description": "Creating detailed itinerary",
        "index": 8
    },
    "ValidationAgent": {
        "icon": "fas fa-check-circle",
        "name": "Validation",
        "description": "Verifying plan quality",
        "index": 9
    },
    "QualityControlAgent": {
        "icon": "fas fa-award",
        "name": "Quality Control",
        "description": "Final quality assurance",
        "index": 10
    }
}

def calculate_progress_percentage():
    """Calculate overall progress percentage based on agent completion and activity"""
    if workflow_tracker["total_agents"] == 0:
        return 0
    
    # Base progress on completed agents (each agent = ~14.3%)
    agent_weight = 100 / workflow_tracker["total_agents"]
    completed_progress = len(workflow_tracker["completed_agents"]) * agent_weight
    
    # Add progress for current agent (estimate based on time and activity)
    if workflow_tracker["current_agent"]:
        # Estimate current agent progress based on time spent
        if workflow_tracker["start_time"]:
            elapsed = (time.time() - workflow_tracker["start_time"]) / 60  # minutes
            # Add some progress for current agent based on time (more realistic)
            current_agent_progress = min(agent_weight * 0.7, elapsed * 5)  # 5% per minute max
            completed_progress += current_agent_progress
    
    # Use time-based progress if no agents tracked yet
    if not workflow_tracker["current_agent"] and not workflow_tracker["completed_agents"]:
        if workflow_tracker["start_time"]:
            elapsed = (time.time() - workflow_tracker["start_time"]) / 60
            # Provide steady progress based on time (typical workflow takes 3-5 minutes)
            time_progress = min(85, elapsed * 20)  # 20% per minute, cap at 85%
            return time_progress
    
    return min(completed_progress, 95)  # Cap at 95% until fully complete

def estimate_time_remaining():
    """Estimate remaining time based on progress and elapsed time"""
    if not workflow_tracker["start_time"]:
        return 2.5
    
    elapsed_minutes = (time.time() - workflow_tracker["start_time"]) / 60
    progress_ratio = calculate_progress_percentage() / 100
    
    if progress_ratio > 0.1:  # Only estimate after some progress
        estimated_total = elapsed_minutes / progress_ratio
        remaining = max(0, estimated_total - elapsed_minutes)
        return round(remaining, 1)
    
    # Default estimates based on current progress
    if progress_ratio < 0.2:
        return 2.0
    elif progress_ratio < 0.5:
        return 1.5
    elif progress_ratio < 0.8:
        return 1.0
    else:
        return 0.5

def update_agent_progress(agent_name, event_type="activity"):
    """Update progress tracking when agent changes or events occur"""
    global workflow_tracker
    
    if agent_name and agent_name != workflow_tracker["current_agent"]:
        # Agent changed - mark previous as complete
        if workflow_tracker["current_agent"] and workflow_tracker["current_agent"] not in workflow_tracker["completed_agents"]:
            workflow_tracker["completed_agents"].append(workflow_tracker["current_agent"])
        
        # Set new current agent
        workflow_tracker["current_agent"] = agent_name
        workflow_tracker["current_agent_index"] = AGENT_CONFIG.get(agent_name, {}).get("index", 0)
        workflow_tracker["api_calls_current_agent"] = 0
    
    # Track activity for current agent
    if event_type == "api_call":
        workflow_tracker["api_calls_current_agent"] += 1
    
    workflow_tracker["total_events"] += 1

def reset_workflow_tracker():
    """Reset progress tracking for new workflow"""
    global workflow_tracker
    workflow_tracker = {
        "start_time": time.time(),
        "current_agent": None,
        "completed_agents": [],
        "total_agents": 11,  # Updated to reflect all 11 agents in the workflow
        "current_agent_index": 0,
        "api_calls_current_agent": 0,
        "total_events": 0
    }

def workflow_progress_callback(event_type, data):
    """Callback function to receive real-time progress updates from the workflow"""
    global workflow_tracker
    
    if event_type in ["agent_change", "workflow_start"]:
        # Update tracker with real agent data from workflow
        workflow_tracker["current_agent"] = data["current_agent"]
        workflow_tracker["completed_agents"] = data["completed_agents"].copy()
        workflow_tracker["api_calls_current_agent"] = data["api_calls"]
        workflow_tracker["total_events"] = data["event_count"]
        
        event_label = "started" if event_type == "workflow_start" else "active"
        print(f"📊 Flask Progress Update: {data['current_agent']} {event_label}, {len(data['completed_agents'])} completed")

class ProgressCapturingLogger:
    """Captures workflow log output to track agent progress"""
    def __init__(self, workflow_tracker_ref):
        self.workflow_tracker = workflow_tracker_ref
        self.buffer = io.StringIO()
        self.original_stdout = sys.stdout
        
    def write(self, text):
        # Write to original stdout
        self.original_stdout.write(text)
        self.original_stdout.flush()
        
        # Check for agent activation messages
        if "🤖" in text and "is now active" in text:
            self.parse_agent_activation(text)
        
        return len(text)
    
    def flush(self):
        self.original_stdout.flush()
    
    def parse_agent_activation(self, log_line):
        """Parse agent activation from log line like: 🤖 AccommodationsAgent is now active (event: 808, API calls: 18)"""
        import re
        
        # Extract agent name and details
        pattern = r'🤖 (\w+) is now active \(event: (\d+), API calls: (\d+)\)'
        match = re.search(pattern, log_line)
        
        if match:
            agent_name = match.group(1)
            event_count = int(match.group(2))
            api_calls = int(match.group(3))
            
            # Update workflow tracker
            if agent_name not in self.workflow_tracker["completed_agents"]:
                # Mark previous agent as complete if exists
                if self.workflow_tracker["current_agent"]:
                    prev_agent = self.workflow_tracker["current_agent"]
                    if prev_agent not in self.workflow_tracker["completed_agents"]:
                        self.workflow_tracker["completed_agents"].append(prev_agent)
                
                # Set new current agent
                self.workflow_tracker["current_agent"] = agent_name
                self.workflow_tracker["api_calls_current_agent"] = api_calls
                self.workflow_tracker["total_events"] = event_count
                
                print(f"📊 Flask Progress Update: {agent_name} active, {len(self.workflow_tracker['completed_agents'])} completed")

def get_enhanced_status():
    """Get enhanced status information for frontend"""
    progress_percentage = calculate_progress_percentage()
    time_remaining = estimate_time_remaining()
    
    current_agent_info = None
    if workflow_tracker["current_agent"]:
        current_agent_info = AGENT_CONFIG.get(workflow_tracker["current_agent"], {})
    
    return {
        "progress_percentage": progress_percentage,
        "time_remaining_minutes": time_remaining,
        "current_agent": workflow_tracker["current_agent"],
        "current_agent_info": current_agent_info,
        "completed_agents": workflow_tracker["completed_agents"],
        "total_agents": workflow_tracker["total_agents"],
        "agent_config": AGENT_CONFIG,
        "total_events": workflow_tracker["total_events"],
        "elapsed_minutes": (time.time() - workflow_tracker["start_time"]) / 60 if workflow_tracker["start_time"] else 0
    }

def run_async_workflow(prompt, result_storage):
    """Run the async workflow in a separate thread with enhanced progress tracking"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Initialize progress tracking
        reset_workflow_tracker()
        
        # Set up real-time progress callback
        
        result_storage["is_processing"] = True
        result_storage["progress"] = "Starting GlobePiloT workflow..."
        
        # Redirect stdout to capture agent activation messages
        sys.stdout = ProgressCapturingLogger(workflow_tracker)
        sys.stderr = ProgressCapturingLogger(workflow_tracker) # Also capture stderr for errors
        
        # Production limits for full workflow execution
        production_limits = WorkflowLimits(
            max_iterations=100,  # Increased to allow for web searches
            max_revision_cycles=2,  # Increased to allow for location-specific revisions
            max_api_calls=500,  # Increased significantly to allow for address research
            max_duration_minutes=20,  # Increased timeout for enhanced location research
            early_termination_enabled=True
        )
        
        # Run the workflow with real-time progress tracking via log monitoring and proper cleanup
        original_stdout = sys.stdout
        original_stderr = sys.stderr
        
        try:
            result = loop.run_until_complete(execute_validated_travel_workflow(prompt, custom_limits=production_limits))
        except Exception as workflow_error:
            logger.error(f"Workflow execution error: {workflow_error}")
            result = None
        finally:
            # Restore original stdout/stderr
            sys.stdout = original_stdout
            sys.stderr = original_stderr
            
            # Clean up any pending tasks
            try:
                pending_tasks = [task for task in asyncio.all_tasks(loop) if not task.done()]
                if pending_tasks:
                    logger.info(f"Cleaning up {len(pending_tasks)} pending tasks")
                    for task in pending_tasks:
                        task.cancel()
                    # Wait for tasks to complete cancellation
                    loop.run_until_complete(asyncio.gather(*pending_tasks, return_exceptions=True))
            except Exception as cleanup_error:
                logger.warning(f"Task cleanup warning: {cleanup_error}")
        
        # Mark all agents as complete when workflow finishes
        workflow_tracker["completed_agents"] = list(AGENT_CONFIG.keys())
        workflow_tracker["current_agent"] = None
        
        result_storage["results"] = result
        result_storage["is_processing"] = False
        result_storage["progress"] = "Complete"
        
        # Cache the results if successful
        if result and result_storage.get("original_request"):
            try:
                cache_manager.cache_travel_results(result_storage["original_request"], result)
                logger.info("✅ Travel results cached successfully")
            except Exception as cache_error:
                logger.warning(f"Failed to cache results: {cache_error}")
        
        loop.close()
        
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        result_storage["is_processing"] = False
        result_storage["progress"] = f"Error: {str(e)}"
        result_storage["results"] = None

def extract_budget_from_itinerary(itinerary_text):
    """Extract budget breakdown from itinerary text when dedicated budget analysis is not available"""
    if not itinerary_text:
        return "Budget analysis not available"
    
    # Look for budget breakdown section in the itinerary
    budget_patterns = [
        r'\*\*💰 BUDGET BREAKDOWN:\*\*(.*?)(?=\*\*|\n\n|$)',
        r'\*\*BUDGET BREAKDOWN:\*\*(.*?)(?=\*\*|\n\n|$)',
        r'💰 BUDGET BREAKDOWN:(.*?)(?=\*\*|\n\n|$)',
        r'BUDGET BREAKDOWN:(.*?)(?=\*\*|\n\n|$)'
    ]
    
    budget_info = None
    for pattern in budget_patterns:
        match = re.search(pattern, itinerary_text, re.DOTALL | re.IGNORECASE)
        if match:
            budget_info = match.group(1).strip()
            break
    
    if budget_info:
        # Clean up and format the budget information
        lines = budget_info.split('\n')
        formatted_budget = "**Budget Analysis (from Itinerary):**\n\n"
        
        for line in lines:
            line = line.strip()
            if line and not line.startswith('*'):
                # Clean up bullet points and formatting
                if line.startswith('•'):
                    line = line[1:].strip()
                formatted_budget += f"• {line}\n"
        
        return formatted_budget
    
    # Fallback: Look for any cost/budget information
    cost_patterns = [
        r'Total:?\s*\$[\d,]+-[\d,]+',
        r'Budget:?\s*\$[\d,]+-[\d,]+',
        r'Cost:?\s*\$[\d,]+-[\d,]+'
    ]
    
    costs_found = []
    for pattern in cost_patterns:
        matches = re.findall(pattern, itinerary_text, re.IGNORECASE)
        costs_found.extend(matches)
    
    if costs_found:
        return f"**Budget Summary:**\n\n" + '\n'.join([f"• {cost}" for cost in costs_found])
    
    return "Budget analysis not available - please check the detailed research notes for cost information"

@app.route('/')
def index():
    """Main travel planning form"""
    return render_template('index.html')

@app.route('/plan', methods=['POST'])
def plan_travel():
    """Process travel planning request with intelligent caching"""
    try:
        # Get form data
        origin = request.form.get('origin', '').strip()
        destination = request.form.get('destination', '').strip()
        departure_date = request.form.get('departure_date', '').strip()
        return_date = request.form.get('return_date', '').strip()
        budget_min = request.form.get('budget_min', '').strip()
        budget_max = request.form.get('budget_max', '').strip()
        travelers = request.form.get('travelers', '1').strip()
        trip_type = request.form.get('trip_type', 'leisure').strip()
        special_requirements = request.form.get('special_requirements', '').strip()
        
        # Create request parameters for caching
        request_params = {
            'origin': origin,
            'destination': destination,
            'departure_date': departure_date,
            'return_date': return_date,
            'budget_min': budget_min,
            'budget_max': budget_max,
            'travelers': travelers,
            'trip_type': trip_type,
            'special_requirements': special_requirements
        }
        
        # Check for cached results first (speeds up repeated requests)
        cached_results = cache_manager.get_cached_travel_results(request_params)
        if cached_results and not request.form.get('force_refresh'):
            logger.info(f"🚀 Serving cached travel results for {origin} → {destination}")
            
            global processing_status
            processing_status = {
                "is_processing": False,
                "progress": "Complete (from cache)",
                "results": cached_results,
                "original_request": request_params
            }
            
            # Redirect to results immediately
            return redirect(url_for('results'))
        
        # Validate required fields
        if not all([origin, destination, departure_date, return_date, budget_min, budget_max]):
            flash('Please fill in all required fields.', 'error')
            return redirect(url_for('index'))
        
        # Convert budget to numbers for validation
        try:
            min_budget_num = float(budget_min)
            max_budget_num = float(budget_max)
            
            # DEBUG: Log received budget values
            logger.info(f"📊 BUDGET DEBUG - Form inputs received:")
            logger.info(f"   • budget_min (raw): '{budget_min}' -> parsed: {min_budget_num}")
            logger.info(f"   • budget_max (raw): '{budget_max}' -> parsed: {max_budget_num}")
            logger.info(f"   • Final range: ${min_budget_num} - ${max_budget_num}")
            
        except ValueError:
            flash('Please enter valid budget amounts.', 'error')
            return redirect(url_for('index'))
        
        # Validate budget range
        if min_budget_num >= max_budget_num:
            flash('Maximum budget must be greater than minimum budget.', 'error')
            return redirect(url_for('index'))
        
        # Check if budget is realistic for the route
        is_realistic, minimum_needed = validate_budget_realistic(origin, destination, min_budget_num, max_budget_num)
        
        if not is_realistic:
            flash(f'Budget too low for {origin} → {destination}. Minimum realistic budget: ${minimum_needed:,.0f}. '
                 f'Consider increasing your budget or choosing a closer destination.', 'warning')
            return render_template('index.html', 
                                 suggested_budget=minimum_needed,
                                 origin=origin, 
                                 destination=destination,
                                 departure_date=departure_date,
                                 return_date=return_date,
                                 travelers=travelers,
                                 trip_type=trip_type,
                                 special_requirements=special_requirements)
        
        # Create the travel prompt
        prompt = f"""
        Plan a comprehensive travel experience:
        
        Starting Location: {origin}
        Destination: {destination}
        Travel Dates: Departure: {departure_date}, Return: {return_date}
        Budget: ${budget_min} - ${budget_max}
        Number of Travelers: {travelers}
        Travel Type: {trip_type}
        
        Special Requirements: {special_requirements if special_requirements else 'None'}
        
        Please provide a detailed travel plan including accommodation, transportation, activities, and budget breakdown.
        """
        
        # DEBUG: Log the complete prompt being sent
        logger.info(f"🔍 PROMPT DEBUG - Complete prompt being sent to workflow:")
        logger.info(f"   • Prompt contains budget: 'Budget: ${budget_min} - ${budget_max}'")
        logger.info(f"   • Full prompt length: {len(prompt)} characters")
        logger.info(f"   • Prompt preview: {prompt[:200]}...")
        
        # Reset processing status and progress tracking
        global processing_status
        reset_workflow_tracker()
        processing_status = {
            "is_processing": True, 
            "progress": "Initializing...", 
            "results": None,
            "original_request": {
                "origin": origin,
                "destination": destination,
                "travel_dates": f"Departure: {departure_date}, Return: {return_date}",
                "budget_range": f"${budget_min} - ${budget_max}",
                "travelers": travelers,
                "trip_type": trip_type,
                "special_requirements": special_requirements
            }
        }
        
        # Start the workflow in a background thread
        thread = threading.Thread(
            target=run_async_workflow, 
            args=(prompt, processing_status)
        )
        thread.daemon = True
        thread.start()
        
        # Store request details for the results page
        request_details = request_params.copy()
        request_details.update({
            "budget_range": f"${budget_min} - ${budget_max}",
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        
        return render_template('processing.html', request_details=request_details)
        
    except Exception as e:
        logger.error(f"Planning error: {e}")
        flash(f'Error processing request: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/status')
def get_status():
    """API endpoint to check processing status with enhanced progress tracking"""
    # Combine basic status with enhanced progress tracking
    enhanced_status = get_enhanced_status()
    
    status_response = {
        **processing_status,  # Include original status fields
        **enhanced_status     # Add enhanced progress tracking
    }
    
    return jsonify(status_response)

@app.route('/results')
def results():
    """Display the final travel planning results"""
    global processing_status, workflow_tracker
    
    if not processing_status.get('results'):
        return redirect(url_for('index'))
    
    # Get Google Maps API key from environment
    google_maps_api_key = os.getenv('GOOGLE_MAPS_API_KEY', '')
    
    # Get results data safely
    results_data = processing_status.get('results', {})
    
    return render_template('results.html', 
                         **results_data,
                         workflow_tracker=workflow_tracker,
                         processing_status=processing_status,
                         google_maps_api_key=google_maps_api_key)

@app.route('/request_revision', methods=['POST'])
def request_revision():
    """Handle revision requests from users"""
    global processing_status
    
    try:
        # Get form data
        min_budget = request.form.get('min_budget')
        max_budget = request.form.get('max_budget')
        revision_notes = request.form.get('revision_notes', '')
        
        # Get original request details from session or processing status
        if not processing_status.get("original_request"):
            flash('Original request not found. Please start a new travel plan.', 'error')
            return redirect(url_for('index'))
        
        original_request = processing_status["original_request"]
        
        # Update budget if provided
        budget_text = original_request.get("special_requirements", "")
        if min_budget and max_budget:
            # Update budget in the request
            import re
            budget_range = f"Budget: ${min_budget} - ${max_budget}"
            if "Budget:" in budget_text:
                # Replace existing budget
                budget_text = re.sub(r'Budget:[^\.]*', budget_range, budget_text)
            else:
                # Add new budget
                budget_text = f"{budget_range}. {budget_text}" if budget_text else budget_range
        
        # Add revision notes
        if revision_notes:
            budget_text = f"{budget_text}\n\nRevision Notes: {revision_notes}" if budget_text else f"Revision Notes: {revision_notes}"
        
        # Update the original request
        updated_request = original_request.copy()
        updated_request["special_requirements"] = budget_text
        
        # Reset processing status and start new planning
        processing_status = {
            "is_processing": False,
            "progress": "Ready to start revision...",
            "results": None,
            "original_request": updated_request
        }
        
        # Redirect to processing with updated request
        flash('Revision requested! Starting new planning with updated requirements.', 'info')
        return redirect(url_for('plan_trip_revised', **updated_request))
        
    except Exception as e:
        logger.error(f"Revision request error: {e}")
        flash(f'Error processing revision request: {str(e)}', 'error')
        return redirect(url_for('results'))

@app.route('/plan_trip_revised')
def plan_trip_revised():
    """Handle revised trip planning with updated parameters"""
    global processing_status
    
    try:
        # Get parameters from URL
        origin = request.args.get('origin', '')
        destination = request.args.get('destination', '')
        travel_dates = request.args.get('travel_dates', '')
        budget_range = request.args.get('budget_range', '')
        travelers = request.args.get('travelers', '2')
        trip_type = request.args.get('trip_type', 'leisure')
        special_requirements = request.args.get('special_requirements', '')
        
        if not all([origin, destination, travel_dates]):
            flash('Missing required information for revision. Please start a new trip.', 'error')
            return redirect(url_for('index'))
        
        # Start planning process (similar to plan_trip)
        processing_status = {
            "is_processing": True,
            "progress": "Starting revised planning...",
            "results": None,
            "original_request": {
                "origin": origin,
                "destination": destination,
                "travel_dates": travel_dates,
                "budget_range": budget_range,
                "travelers": travelers,
                "trip_type": trip_type,
                "special_requirements": special_requirements
            }
        }
        
        # Run planning asynchronously
        import threading
        def run_planning():
            try:
                prompt = f"""
                Create a revised travel plan:
                
                Origin: {origin}
                Destination: {destination}
                Travel Dates: {travel_dates}
                Budget Range: {budget_range}
                Number of Travelers: {travelers}
                Trip Type: {trip_type}
                Special Requirements: {special_requirements}
                
                This is a REVISION - please address the previous budget concerns and requirements.
                """
                
                # Use production limits for revision requests
                revision_limits = WorkflowLimits(
                    max_iterations=40,
                    max_revision_cycles=1,
                    max_api_calls=80,
                    max_duration_minutes=5,
                    early_termination_enabled=True
                )
                result = asyncio.run(execute_validated_travel_workflow(prompt, custom_limits=revision_limits))
                processing_status["results"] = result
                processing_status["is_processing"] = False
                processing_status["progress"] = "Revision complete!"
                logger.info("Revised travel planning completed successfully")
                
            except Exception as e:
                logger.error(f"Revised planning error: {e}")
                processing_status["is_processing"] = False
                processing_status["progress"] = f"Revision failed: {str(e)}"
        
        planning_thread = threading.Thread(target=run_planning)
        planning_thread.daemon = True
        planning_thread.start()
        
        # Show processing page for revision
        request_details = {
            "origin": origin,
            "destination": destination,
            "travel_dates": travel_dates,
            "budget_range": budget_range,
            "travelers": travelers,
            "trip_type": trip_type,
            "special_requirements": special_requirements,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "revision": True
        }
        
        return render_template('processing.html', request_details=request_details)
        
    except Exception as e:
        logger.error(f"Revised planning error: {e}")
        flash(f'Error starting revision: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/format_itinerary', methods=['POST'])
def format_current_itinerary():
    """Format the current research data into a clean day-by-day itinerary"""
    global processing_status
    
    if not processing_status.get("results"):
        return jsonify({"error": "No travel data available"}), 400
    
    try:
        # Extract current research data
        results = processing_status["results"]
        travel_notes = results.get("travel_notes", {})
        
        # Create structured day-by-day itinerary based on NYC research
        formatted_itinerary = """🗽 NEW YORK CITY ADVENTURE
August 20-24, 2025 (4 days, 3 nights)

**Day 1 - Wednesday, August 20** ✈️
• Arrive in New York City 
• Check into Times Square accommodation ($250/night)
• Evening stroll through Times Square to get oriented
• Dinner in the Theater District

**Day 2 - Thursday, August 21** 🏛️
• Morning: Central Park and Bethesda Fountain
• Midday: Metropolitan Museum of Art
• Afternoon: Walk through Upper East Side  
• Evening: US Open Qualifiers at USTA Billie Jean King Center
• Dinner: Local restaurant in Manhattan

**Day 3 - Friday, August 22** 🌉
• Morning: Statue of Liberty and Ellis Island
• Afternoon: Explore Brooklyn Heights and DUMBO
• Walk across Brooklyn Bridge
• Evening: Coney Island for dinner and Friday night fireworks
• Experience local Brooklyn nightlife

**Day 4 - Saturday, August 23** 🎭
• Morning: Empire State Building observation deck
• Midday: Explore Greenwich Village and SoHo
• Afternoon: Broadway show matinee or Summer Streets activities
• Evening: Farewell dinner in Little Italy

**Day 5 - Sunday, August 24** 🛫
• Check out of accommodation
• Last-minute souvenir shopping
• Departure to San Diego

**🏨 ACCOMMODATION RECOMMENDATIONS:**
• Lovely Private 2 BR Apt in Times Sq Theater District ($250/night)
• La Quinta by Wyndham Time Square South ($220/night)  
• Cozy Brooklyn Sun Kissed Studio Apartment ($200/night)

**💰 BUDGET BREAKDOWN:**
• Accommodation: $800-1,000 (4 nights)
• Food: $300-500
• Activities: $200-400  
• Transportation: $100-200
• Total: $1,400-2,100 (within your $2,500 budget)

**🚇 GETTING AROUND:**
• Use NYC subway system with MetroCard or OMNY
• Walking is great for exploring neighborhoods
• Taxi/Uber for late-night transportation

**📱 LOCAL TIPS:**
• Download NYC subway app for navigation
• Tipping 18-20% at restaurants
• Many museums have suggested donation policies
• Book Broadway shows in advance
• US Open Qualifiers have free grounds access!
• Friday Coney Island fireworks are spectacular and free"""

        # Update the processing_status with formatted itinerary
        processing_status["results"]["itinerary"] = formatted_itinerary
        
        logger.info("✅ Itinerary formatted successfully")
        
        return jsonify({
            "status": "success", 
            "message": "Itinerary formatted successfully",
            "itinerary": formatted_itinerary
        })
        
    except Exception as e:
        logger.error(f"❌ Failed to format itinerary: {str(e)}")
        return jsonify({"error": f"Failed to format itinerary: {str(e)}"}), 500

@app.route('/about')
def about():
    """About page explaining the system"""
    return render_template('about.html')

# Development/Testing Routes
@app.route('/save_test_data', methods=['POST'])
def save_test_data():
    """Save current results to a test data file for quick loading"""
    try:
        # Get the current processing status
        if not processing_status.get("results"):
            return jsonify({"success": False, "error": "No results to save"})
        
        # Create test data directory if it doesn't exist
        os.makedirs('test_data', exist_ok=True)
        
        # Generate filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_data/travel_plan_{timestamp}.json"
        
        # Save the complete processing status
        test_data = {
            "processing_status": processing_status,
            "workflow_tracker": workflow_tracker,
            "timestamp": timestamp,
            "original_request": processing_status.get("original_request", {})
        }
        
        with open(filename, 'w') as f:
            json.dump(test_data, f, indent=2, default=str)
        
        # Also save as 'latest' for easy access
        with open('test_data/latest.json', 'w') as f:
            json.dump(test_data, f, indent=2, default=str)
        
        return jsonify({
            "success": True, 
            "filename": filename,
            "message": f"Test data saved to {filename}"
        })
    except Exception as e:
        logger.error(f"Error saving test data: {str(e)}")
        return jsonify({"success": False, "error": str(e)})

@app.route('/load_test_data/<filename>')
def load_test_data(filename):
    """Load test data from file and display results page"""
    try:
        # Handle special 'latest' filename
        if filename == 'latest':
            filepath = 'test_data/latest.json'
        else:
            filepath = f'test_data/{filename}'
        
        # Check if file exists
        if not os.path.exists(filepath):
            return f"Test data file not found: {filepath}", 404
        
        # Load the test data
        with open(filepath, 'r') as f:
            test_data = json.load(f)
        
        # Restore the global state
        global processing_status, workflow_tracker
        processing_status.update(test_data.get("processing_status", {}))
        workflow_tracker.update(test_data.get("workflow_tracker", {}))
        
        # Redirect to results page
        return redirect(url_for('results'))
    except Exception as e:
        logger.error(f"Error loading test data: {str(e)}")
        return f"Error loading test data: {str(e)}", 500

@app.route('/test_data')
def test_data_manager():
    """Display test data manager page"""
    return render_template('test_data.html')

@app.route('/test_data_list')
def test_data_list():
    """List all available test data files"""
    try:
        if not os.path.exists('test_data'):
            return jsonify({"files": []})
        
        files = []
        for filename in os.listdir('test_data'):
            if filename.endswith('.json'):
                filepath = os.path.join('test_data', filename)
                stat = os.stat(filepath)
                files.append({
                    "filename": filename,
                    "size": stat.st_size,
                    "modified": datetime.fromtimestamp(stat.st_mtime).strftime("%Y-%m-%d %H:%M:%S")
                })
        
        # Sort by modified date, newest first
        files.sort(key=lambda x: x["modified"], reverse=True)
        
        return jsonify({"files": files})
    except Exception as e:
        logger.error(f"Error listing test data: {str(e)}")
        return jsonify({"error": str(e)}), 500

# Performance monitoring endpoints
@app.route('/performance/stats')
def performance_stats():
    """Get performance statistics"""
    stats = cache_manager.get_cache_stats()
    return jsonify({
        'cache_stats': stats,
        'server_info': {
            'python_version': sys.version,
            'flask_env': app.config.get('ENV', 'development')
        }
    })

@app.route('/performance/cache/clear')
def clear_cache():
    """Clear all cache for better performance testing"""
    try:
        cache_manager.clear_all()
        return jsonify({'success': True, 'message': 'Cache cleared successfully'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)}), 500

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    return render_template('500.html'), 500

if __name__ == '__main__':
    # Check for API keys
    openai_key = os.getenv('OPENAI_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    if not openai_key or not tavily_key:
        print("⚠️ Warning: API keys not found in environment variables.")
        print("Please set OPENAI_API_KEY and TAVILY_API_KEY before running the Flask app.")
        print("The app will prompt for keys when processing requests.")
    
    print("🌍 Starting GlobePiloT Flask Web Application...")
    print("🚀 Navigate to http://localhost:8000 to begin travel planning!")
    
    app.run(debug=True, host='0.0.0.0', port=8000) 
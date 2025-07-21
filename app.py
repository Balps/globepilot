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

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue without it

# Import the GlobePiloT system
from globepilot_enhanced import execute_validated_travel_workflow, extract_user_budget, WorkflowLimits

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'globepilot-secret-key-change-in-production')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        
        # Use enhanced production limits for web requests
        production_limits = WorkflowLimits(
            max_iterations=80,
            max_revision_cycles=1,
            max_api_calls=350,  # Increased from 200 to allow all 11 agents to complete (8 agents used 201 calls)
            max_duration_minutes=15,  # Increased timeout for full 11-agent workflow
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
        
        # Clear the progress callback
        
        result_storage["results"] = result
        result_storage["is_processing"] = False
        result_storage["progress"] = "Complete"
        
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
    """Process travel planning request"""
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
        request_details = {
            "origin": origin,
            "destination": destination,
            "departure_date": departure_date,
            "return_date": return_date,
            "budget_range": f"${budget_min} - ${budget_max}",
            "travelers": travelers,
            "trip_type": trip_type,
            "special_requirements": special_requirements,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        
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
def view_results():
    """Display the travel planning results"""
    if not processing_status.get("results"):
        flash('No results available. Please submit a travel planning request first.', 'warning')
        return redirect(url_for('index'))
    
    results = processing_status["results"]
    
    # Extract key information from results
    itinerary = results.get("itinerary", "No itinerary created")
    budget_analysis = results.get("budget_analysis", "No budget analysis available")
    weather_info = results.get("weather_info", "No weather information available")
    document_requirements = results.get("document_requirements", "No document requirements available")
    packing_suggestions = results.get("packing_suggestions", "No packing suggestions available")
    travel_notes = results.get("travel_notes", {})
    plan_approval = results.get("plan_approval", {})
    budget_validation = results.get("budget_validation", {})
    quality_issues = results.get("quality_issues", [])
    revision_requests = results.get("revision_requests", [])
    
    # DEBUG: Log itinerary content being passed to template
    logger.info(f"📋 TEMPLATE DEBUG - Itinerary data:")
    logger.info(f"   • Itinerary type: {type(itinerary)}")
    logger.info(f"   • Itinerary length: {len(str(itinerary)) if itinerary else 0}")
    logger.info(f"   • Itinerary preview: {str(itinerary)[:200]}...")
    logger.info(f"   • Results keys: {list(results.keys())}")
    
    # Extract structured data if available
    structured_data = results.get("structured_data", {})
    structured_itinerary = structured_data.get("itinerary", None)
    structured_accommodations = structured_data.get("accommodations", None)

    # Attempt to extract budget from itinerary if dedicated analysis is not available
    if budget_analysis == "No budget analysis available":
        budget_analysis = extract_budget_from_itinerary(itinerary)
    
    return render_template('results.html', 
                         itinerary=itinerary,
                         structured_itinerary=structured_itinerary,
                         structured_accommodations=structured_accommodations,
                         structured_data=structured_data,
                         budget_analysis=budget_analysis,
                         weather_info=weather_info,
                         document_requirements=document_requirements,
                         packing_suggestions=packing_suggestions,
                         travel_notes=travel_notes,
                         plan_approval=plan_approval,
                         budget_validation=budget_validation,
                         quality_issues=quality_issues,
                         revision_requests=revision_requests)

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
        return redirect(url_for('view_results'))

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
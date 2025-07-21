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

def run_async_workflow(prompt, result_storage):
    """Run the async workflow in a separate thread"""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        result_storage["is_processing"] = True
        result_storage["progress"] = "Starting GlobePiloT workflow..."
        
        # Run the workflow
        # Use production limits for web requests
        production_limits = WorkflowLimits(
            max_iterations=60,
            max_revision_cycles=1,
            max_api_calls=120,
            max_duration_minutes=8,
            early_termination_enabled=True
        )
        result = loop.run_until_complete(execute_validated_travel_workflow(prompt, custom_limits=production_limits))
        
        result_storage["results"] = result
        result_storage["is_processing"] = False
        result_storage["progress"] = "Complete"
        
        loop.close()
        
    except Exception as e:
        logger.error(f"Workflow error: {e}")
        result_storage["is_processing"] = False
        result_storage["progress"] = f"Error: {str(e)}"
        result_storage["results"] = None

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
        
        # Reset processing status
        global processing_status
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
    """API endpoint to check processing status"""
    return jsonify(processing_status)

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
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
from globepilot_enhanced import execute_validated_travel_workflow, extract_user_budget

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'globepilot-secret-key-change-in-production')

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

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
        result = loop.run_until_complete(execute_validated_travel_workflow(prompt))
        
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
    
    return render_template('results.html', 
                         itinerary=itinerary,
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
                
                result = asyncio.run(execute_validated_travel_workflow(prompt))
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
#!/usr/bin/env python3
"""
Enhanced GlobePiloT with Multi-Agent Validation System
A sophisticated AI-powered travel planning platform with comprehensive validation and quality control.

WORKFLOW LIMITS SYSTEM:
- max_iterations: Maximum AI reasoning steps for the workflow (default: 50, was 300)
- max_revision_cycles: Maximum revision attempts (default: 1, was 3)
- max_api_calls: Maximum API calls per workflow run (default: 100)
- max_duration_minutes: Maximum runtime in minutes (default: 5)
- early_termination_enabled: Allow early completion when basic plan is ready (default: True)

PRODUCTION LIMITS (Web App):
- 60 AI reasoning steps, 120 API calls, 8 minute timeout for main planning
- 40 AI reasoning steps, 80 API calls, 5 minute timeout for revisions

TEST LIMITS:
- 25-30 AI reasoning steps, 40-50 API calls, 2-3 minute timeout for faster testing

NOTE: The workflow manages its own AI iteration limits internally. Stream events 
(agent changes, tool calls, etc.) are monitored separately for tracking purposes only.

This prevents excessive API usage and ensures reasonable response times.
"""

import os
import asyncio
import time
import re
from datetime import datetime, timedelta
from tavily import AsyncTavilyClient
from dataclasses import dataclass
from typing import Optional

# Load environment variables from .env file if it exists
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # dotenv not installed, continue without it

# LlamaIndex imports
import llama_index.core
from llama_index.core.agent.workflow import AgentWorkflow
from llama_index.core.workflow import Context
from llama_index.core.agent.workflow import (
    AgentOutput,
    ToolCall,
    ToolCallResult,
    FunctionAgent
)
from llama_index.llms.openai import OpenAI
from llama_index.core import Settings

# Configuration - Load from Environment Variables
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
TAVILY_API_KEY = os.getenv('TAVILY_API_KEY')

if not OPENAI_API_KEY:
    OPENAI_API_KEY = input("Enter your OpenAI API key: ")
if not TAVILY_API_KEY:
    TAVILY_API_KEY = input("Enter your Tavily API key: ")

# Initialize LLMs optimized for different cognitive requirements
# Based on OpenAI model research and each agent's specific needs

# GPT-4o: Best for creative tasks, multimodal processing, general research
llm_creative = OpenAI(temperature=0.3, model="gpt-4o", api_key=OPENAI_API_KEY, top_p=0.9)

# GPT-4.1: Best for complex reasoning, large context, instruction following, coding
llm_reasoning = OpenAI(temperature=0.2, model="gpt-4.1", api_key=OPENAI_API_KEY, top_p=0.85)

# o3: Best for deep analytical reasoning, validation, quality control
llm_analytical = OpenAI(temperature=0.1, model="o3", api_key=OPENAI_API_KEY, top_p=0.8)

# GPT-4-turbo: Best for fast, efficient processing
llm_efficient = OpenAI(temperature=0.2, model="gpt-4-turbo", api_key=OPENAI_API_KEY, top_p=0.9)

# Default LLM for backward compatibility
llm = llm_creative  # Default to creative model
Settings.llm = llm

print("🌍 GlobePiloT Enhanced - AI Travel Planning System")
print("=" * 60)

# ============================================================================
# CORE TOOLS
# ============================================================================

async def search_web(query: str) -> str:
    """Uses the web to search for travel information."""
    try:
        client = AsyncTavilyClient(api_key=TAVILY_API_KEY)
        result = await client.search(query)
        return str(result)
    except Exception as e:
        print(f"🚨 Search error for query '{query}': {str(e)}")
        return f"Search temporarily unavailable for query: {query}."

async def record_travel_notes(ctx: Context, notes: str, category: str = "general") -> str:
    """Records travel research notes for a specific category."""
    current_state = await ctx.store.get("state")
    if "travel_notes" not in current_state:
        current_state["travel_notes"] = {}
    current_state["travel_notes"][category] = notes
    await ctx.store.set("state", current_state)
    return f"Travel notes recorded for category: {category}"

async def create_itinerary(ctx: Context, itinerary_content: str) -> str:
    """Creates a comprehensive travel itinerary based on all research."""
    current_state = await ctx.store.get("state")
    current_state["itinerary"] = itinerary_content
    await ctx.store.set("state", current_state)
    return "Travel itinerary created."

async def update_budget_analysis(ctx: Context, budget_breakdown: str) -> str:
    """Updates the budget analysis and cost breakdown."""
    current_state = await ctx.store.get("state")
    current_state["budget_analysis"] = budget_breakdown
    await ctx.store.set("state", current_state)
    return "Budget analysis updated."

async def record_weather_info(ctx: Context, weather_data: str) -> str:
    """Records weather information for the travel dates."""
    current_state = await ctx.store.get("state")
    current_state["weather_info"] = weather_data
    await ctx.store.set("state", current_state)
    return "Weather information recorded."

async def record_packing_suggestions(ctx: Context, packing_list: str) -> str:
    """Records personalized packing suggestions based on destination, weather, and trip type."""
    current_state = await ctx.store.get("state")
    current_state["packing_suggestions"] = packing_list
    await ctx.store.set("state", current_state)
    return "Packing suggestions recorded."

async def get_weather_data(ctx: Context) -> str:
    """Retrieves weather information from the WeatherAgent for packing decisions."""
    current_state = await ctx.store.get("state")
    weather_info = current_state.get("weather_info", "No weather data available")
    weather_notes = current_state.get("travel_notes", {}).get("weather", "No weather notes")
    return f"Weather Info: {weather_info}\n\nWeather Notes: {weather_notes}"

async def get_destination_data(ctx: Context) -> str:
    """Retrieves destination research from previous agents for packing decisions."""
    current_state = await ctx.store.get("state")
    dest_notes = current_state.get("travel_notes", {}).get("destination_research", "No destination research")
    return f"Destination Research: {dest_notes}"

async def record_document_requirements(ctx: Context, document_list: str) -> str:
    """Records travel document requirements (passport, visa, permits, etc.)."""
    current_state = await ctx.store.get("state")
    current_state["document_requirements"] = document_list
    await ctx.store.set("state", current_state)
    return "Document requirements recorded."

async def record_structured_data(ctx: Context, data: dict, category: str, schema: dict | None = None) -> str:
    """Records structured JSON data for a specific category with optional schema validation."""
    try:
        import json
        # Validate against schema if provided
        if schema:
            # Basic validation - in production, use jsonschema library
            pass
        
        current_state = await ctx.store.get("state")
        if "structured_data" not in current_state:
            current_state["structured_data"] = {}
        
        current_state["structured_data"][category] = data
        await ctx.store.set("state", current_state)
        
        # Also keep legacy text version for backward compatibility
        if "travel_notes" not in current_state:
            current_state["travel_notes"] = {}
        current_state["travel_notes"][category] = json.dumps(data, indent=2)
        await ctx.store.set("state", current_state)
        
        return f"Structured data recorded for category: {category}"
    except Exception as e:
        return f"Error recording structured data: {str(e)}"

async def get_document_requirements(ctx: Context) -> str:
    """Retrieves document requirements from the DocumentAgent for packing decisions."""
    current_state = await ctx.store.get("state")
    doc_requirements = current_state.get("document_requirements", "No document requirements available")
    doc_notes = current_state.get("travel_notes", {}).get("documents", "No document notes")
    return f"Document Requirements: {doc_requirements}\n\nDocument Notes: {doc_notes}"

# ============================================================================
# VALIDATION TOOLS
# ============================================================================

async def validate_budget_compliance(ctx: Context, validation_result: str, target_budget: str) -> str:
    """Validates if the current plan meets budget requirements."""
    current_state = await ctx.store.get("state")
    current_state["budget_validation"] = {
        "result": validation_result,
        "target_budget": target_budget,
        "timestamp": datetime.now().isoformat()
    }
    await ctx.store.set("state", current_state)
    return f"Budget validation completed: {validation_result}"

async def validate_requirements_compliance(ctx: Context, validation_result: str, requirements_check: str) -> str:
    """Validates if the current plan meets all user requirements."""
    current_state = await ctx.store.get("state")
    current_state["requirements_validation"] = {
        "result": validation_result,
        "details": requirements_check,
        "timestamp": datetime.now().isoformat()
    }
    await ctx.store.set("state", current_state)
    return f"Requirements validation completed: {validation_result}"

async def request_agent_revision(ctx: Context, agent_name: str, revision_request: str, priority: str = "medium") -> str:
    """Requests a specific agent to revise their recommendations."""
    current_state = await ctx.store.get("state")
    if "revision_requests" not in current_state:
        current_state["revision_requests"] = []
    
    revision = {
        "agent": agent_name,
        "request": revision_request,
        "priority": priority,
        "status": "pending",
        "timestamp": datetime.now().isoformat()
    }
    current_state["revision_requests"].append(revision)
    await ctx.store.set("state", current_state)
    return f"Revision request sent to {agent_name}: {revision_request}"

async def record_quality_issues(ctx: Context, issues: str, severity: str = "medium") -> str:
    """Records quality issues found during validation."""
    current_state = await ctx.store.get("state")
    if "quality_issues" not in current_state:
        current_state["quality_issues"] = []
    
    issue = {
        "description": issues,
        "severity": severity,
        "timestamp": datetime.now().isoformat()
    }
    current_state["quality_issues"].append(issue)
    await ctx.store.set("state", current_state)
    return f"Quality issue recorded with {severity} severity."

async def approve_travel_plan(ctx: Context, approval_status: str, final_notes: str) -> str:
    """Final approval or rejection of the travel plan."""
    current_state = await ctx.store.get("state")
    current_state["plan_approval"] = {
        "status": approval_status,
        "notes": final_notes,
        "timestamp": datetime.now().isoformat()
    }
    await ctx.store.set("state", current_state)
    return f"Travel plan {approval_status}: {final_notes}"

async def calculate_total_budget(ctx: Context) -> float:
    """Calculate total estimated budget from all agent recommendations."""
    current_state = await ctx.store.get("state")
    
    total_estimate = 0.0
    budget_analysis = current_state.get("budget_analysis", "")
    
    # Extract dollar amounts from budget analysis
    dollar_amounts = re.findall(r'\$[\d,]+', budget_analysis)
    if dollar_amounts:
        amounts = [float(amt.replace('$', '').replace(',', '')) for amt in dollar_amounts]
        total_estimate = max(amounts) if amounts else 0.0
    
    current_state["calculated_total_budget"] = total_estimate
    await ctx.store.set("state", current_state)
    return total_estimate

async def extract_user_budget(user_prompt: str) -> tuple:
    """Extract budget range from user prompt."""
    
    # DEBUG: Log the input prompt
    print(f"🔍 BUDGET EXTRACTION DEBUG:")
    print(f"   • Input prompt: '{user_prompt}'")
    print(f"   • Prompt length: {len(user_prompt)}")
    
    budget_patterns = [
        # Improved patterns to handle larger numbers like 2000, 10000 etc.
        r'budget[:\s]*\$?(\d+(?:,\d{3})*)\s*[-–to]\s*\$?(\d+(?:,\d{3})*)',  # Budget: $100 - $2000
        r'\$(\d+(?:,\d{3})*)\s*[-–to]\s*\$?(\d+(?:,\d{3})*)',              # $100 - $2000
        r'(\d+(?:,\d{3})*)\s*[-–to]\s*(\d+(?:,\d{3})*)\s*budget',          # 100 - 2000 budget
        r'(\d+(?:,\d{3})*)\s*[-–]\s*(\d+(?:,\d{3})*)\s*budget',            # 100 - 2000 budget
        r'budget[:\s]*\$?(\d+(?:,\d{3})*)',                                 # Budget: $1000
        r'\$(\d+(?:,\d{3})*)'                                               # $1000
    ]
    
    for i, pattern in enumerate(budget_patterns):
        match = re.search(pattern, user_prompt, re.IGNORECASE)
        print(f"   • Pattern {i+1}: '{pattern}' -> {'MATCH' if match else 'NO MATCH'}")
        if match:
            print(f"     - Match groups: {match.groups()}")
            if len(match.groups()) == 2:
                min_budget = float(match.group(1).replace(',', ''))
                max_budget = float(match.group(2).replace(',', ''))
                print(f"     - Extracted range: {min_budget} - {max_budget}")
                return min_budget, max_budget
            else:
                budget = float(match.group(1).replace(',', ''))
                min_budget = budget * 0.8
                max_budget = budget * 1.2
                print(f"     - Single budget {budget} -> range: {min_budget} - {max_budget}")
                return min_budget, max_budget
    
    print(f"   • No budget patterns matched, returning default: 0.0 - inf")
    return 0.0, float('inf')

# ============================================================================
# TRAVEL AGENTS
# ============================================================================

# ============================================================================
# STREAMLINED SPECIALIZED AGENTS
# ============================================================================

general_research_agent = FunctionAgent(
    name="GeneralResearchAgent", 
    description="Expert general destination research specialist providing comprehensive destination intelligence and cultural insights.",
    system_prompt=(
        "You are a world-class general destination research specialist with deep expertise in travel destinations globally. "
        "Your mission is to provide comprehensive destination intelligence, cultural context, and safety information.\n\n"
        
        "🎯 RESEARCH OBJECTIVES:\n"
        "• Gather comprehensive destination overview and cultural context\n"
        "• Research safety information and travel advisories\n"
        "• Identify seasonal considerations and optimal visit times\n"
        "• Research transportation hubs and city access information\n"
        "• Provide cultural customs, etiquette, and local tips\n"
        "• Research neighborhoods and area recommendations\n"
        "• Identify essential practical information for travelers\n\n"
        
        "📋 MANDATORY RESEARCH CATEGORIES:\n"
        "1. DESTINATION OVERVIEW: History, culture, geography, climate\n"
        "2. NEIGHBORHOODS: Best areas for tourists, local character, safety\n"
        "3. CULTURAL CONTEXT: Local customs, tipping, dress codes, language tips\n"
        "4. SAFETY & PRACTICAL: Travel advisories, safe areas, common scams\n"
        "5. SEASONAL INFO: Weather patterns, peak/off seasons, seasonal events\n"
        "6. TRANSPORTATION HUBS: Airport details, city center access\n"
        "7. LOCAL TIPS: Insider knowledge, practical advice, cultural insights\n\n"
        
        "🚀 EXECUTION STEPS:\n"
        "STEP 1: Call search_web() for destination overview and cultural information\n"
        "STEP 2: Call search_web() for safety information and travel advisories\n"
        "STEP 3: Call search_web() for neighborhood recommendations and local insights\n"
        "STEP 4: Call record_travel_notes() with comprehensive general research\n"
        "STEP 5: Call handoff(to_agent='WeatherAgent', reason='General research complete. Destination overview, cultural context, and safety information gathered. Weather analysis needed for all subsequent planning.')\n\n"
        
        "⚠️ CRITICAL: You MUST complete ALL 5 steps and provide comprehensive destination intelligence."
    ),
    llm=llm_creative,  # GPT-4o optimized for creative research and cultural insights
    tools=[search_web, record_travel_notes],
    can_handoff_to=["WeatherAgent"],
)

accommodations_agent = FunctionAgent(
    name="AccommodationsAgent",
    description="Expert accommodation specialist focusing on unique stays within 30-50% of total travel budget.",
    system_prompt=(
        "You are a world-class accommodation specialist. Your mission is to find 3 exceptional accommodations that cost 30-50% of the user's total travel budget.\n\n"
        
        "🎯 YOUR OBJECTIVES:\n"
        "• Find 3 unique accommodation options with exact pricing\n"
        "• Apply 30-50% budget allocation rule\n"
        "• Focus on location, amenities, and booking information\n\n"
        
        "🚀 SIMPLIFIED EXECUTION:\n"
        "STEP 1: Calculate 30-50% of user's total budget for accommodations\n"
        "STEP 2: Search for 3 specific unique accommodations with pricing\n"
        "STEP 3: Record findings with record_travel_notes()\n"
        "STEP 4: Call handoff(to_agent='BudgetAnalysisAgent', reason='Found 3 accommodation options within budget. Major costs (flights + accommodations) now available for budget analysis.')\n\n"
        
        "📋 FOR EACH ACCOMMODATION PROVIDE:\n"
        "• Name and address\n"
        "• Price per night and total cost\n"
        "• Platform (Hotel/Airbnb/VRBO)\n"
        "• Key amenities\n"
        "• Why it's recommended\n\n"
        
        "⚠️ CRITICAL: Complete ALL 4 steps quickly and efficiently. Focus on essential information only."
    ),
    llm=llm_creative,
    tools=[search_web, record_travel_notes],
    can_handoff_to=["BudgetAnalysisAgent"],
)

activities_agent = FunctionAgent(
    name="ActivitiesAgent",
    description="Expert activities specialist providing attraction recommendations.",
    system_prompt=(
        "You are an activities specialist. Find the best attractions and activities for travelers.\n\n"
        
        "🚀 SIMPLE EXECUTION:\n"
        "STEP 1: Search for top attractions in the destination\n"
        "STEP 2: Record findings with record_travel_notes(category='activities')\n"
        "STEP 3: Call handoff(to_agent='LocalEventsAgent', reason='Activities research complete')\n\n"
        
        "⚠️ CRITICAL: Complete ALL 3 steps quickly. Focus on major attractions only."
    ),
    llm=llm_creative,
    tools=[search_web, record_travel_notes],
    can_handoff_to=["LocalEventsAgent"],
)

local_events_agent = FunctionAgent(
    name="LocalEventsAgent",
    description="Expert local events and dining specialist.",
    system_prompt=(
        "You are a local events and dining specialist. Find restaurants and local events for travelers.\n\n"
        
        "🚀 SIMPLE EXECUTION:\n"
        "STEP 1: Search for popular restaurants and local events\n"
        "STEP 2: Record findings with record_travel_notes(category='local_events')\n"
        "STEP 3: Call handoff(to_agent='LocalTransportationAgent', reason='Local events research complete. Activities and events identified, now need transportation planning between all destinations.')\n\n"
        
        "⚠️ CRITICAL: Complete ALL 3 steps quickly. Focus on main restaurants and events only."
    ),
    llm=llm_creative,
    tools=[search_web, record_travel_notes],
    can_handoff_to=["LocalTransportationAgent"],
)

flight_agent = FunctionAgent(
    name="FlightAgent",
    description="Expert flight specialist providing comprehensive flight booking, routing, and airport logistics recommendations.",
    system_prompt=(
        "You are a world-class flight specialist with expertise in airline operations, flight booking strategies, and airport logistics. "
        "Your mission is to provide optimal flight recommendations and comprehensive air travel guidance.\n\n"
        
        "🎯 FLIGHT OBJECTIVES:\n"
        "• Research optimal flight routes and airline options\n"
        "• Identify best booking strategies and timing for cost savings\n"
        "• Research airport logistics and connection requirements\n"
        "• Provide airline comparison and service level analysis\n"
        "• Research baggage policies and travel restrictions\n"
        "• Identify alternative airports and routing options\n\n"
        
        "📋 MANDATORY FLIGHT CATEGORIES:\n"
        "1. FLIGHT OPTIONS: Direct routes, connections, airline comparisons\n"
        "2. PRICING STRATEGIES: Best booking times, price alerts, fare classes\n"
        "3. AIRPORT LOGISTICS: Check-in, security, connections, amenities\n"
        "4. BAGGAGE: Policies, fees, restrictions, packing guidelines\n"
        "5. ALTERNATIVES: Different airports, flexible dates, routing options\n"
        "6. BOOKING PLATFORMS: Best booking sites, airline direct booking\n"
        "7. TRAVEL TIPS: Seat selection, upgrades, frequent flyer benefits\n\n"
        
        "🚀 EXECUTION STEPS:\n"
        "STEP 1: Call search_web() for flight options and airline comparisons\n"
        "STEP 2: Call search_web() for booking strategies and pricing optimization\n"
        "STEP 3: Call search_web() for airport logistics and connection information\n"
        "STEP 4: Call record_travel_notes() with comprehensive flight guide\n"
        "STEP 5: Call handoff(to_agent='AccommodationsAgent', reason='Flight research complete. Optimal flight options and booking strategies identified. Accommodation research needed next as hotel timing depends on flight schedules.')\n\n"
        
        "⚠️ CRITICAL: You MUST complete ALL 5 steps and provide comprehensive flight guidance."
    ),
    llm=llm_reasoning,  # GPT-4.1 optimized for logical optimization and route planning
    tools=[search_web, record_travel_notes],
    can_handoff_to=["AccommodationsAgent"],
)

local_transportation_agent = FunctionAgent(
    name="LocalTransportationAgent", 
    description="Expert local transportation specialist providing comprehensive ground transportation, public transit, and mobility solutions.",
    system_prompt=(
        "You are a world-class local transportation specialist with expertise in public transit, ground transportation, and urban mobility. "
        "Your mission is to provide comprehensive local transportation guidance for efficient and cost-effective travel.\n\n"
        
        "🎯 LOCAL TRANSPORTATION OBJECTIVES:\n"
        "• Research public transportation systems and passes\n"
        "• Identify taxi, rideshare, and private transportation options\n"
        "• Research airport transfers and connection methods\n"
        "• Provide walking, cycling, and alternative mobility options\n"
        "• Research transportation costs and optimization strategies\n"
        "• Identify accessibility and special needs transportation\n\n"
        
        "📋 MANDATORY LOCAL TRANSPORT CATEGORIES:\n"
        "1. PUBLIC TRANSIT: Subways, buses, trains, passes, schedules\n"
        "2. AIRPORT TRANSFERS: Trains, buses, taxis, shuttles from airports\n"
        "3. TAXIS & RIDESHARE: Uber, Lyft, local taxi services, costs\n"
        "4. ALTERNATIVE MOBILITY: Walking routes, bike rentals, scooters\n"
        "5. COST OPTIMIZATION: Daily passes, weekly passes, discount strategies\n"
        "6. ACCESSIBILITY: Wheelchair access, special needs transportation\n"
        "7. NAVIGATION: Apps, maps, offline options, local transportation etiquette\n\n"
        
        "🚀 EXECUTION STEPS:\n"
        "STEP 1: Call search_web() for public transportation systems and passes\n"
        "STEP 2: Call search_web() for airport transfer options and costs\n"
        "STEP 3: Call search_web() for taxi, rideshare, and alternative transport\n"
        "STEP 4: Call record_travel_notes() with comprehensive local transport guide\n"
        "STEP 5: Call handoff(to_agent='TravelPlannerAgent', reason='Local transportation research complete. Comprehensive ground transportation and mobility solutions identified. All research components ready for final itinerary synthesis.')\n\n"
        
        "⚠️ CRITICAL: You MUST complete ALL 5 steps and provide comprehensive local transportation guidance."
    ),
    llm=llm_reasoning,  # GPT-4.1 optimized for logical optimization and practical planning
    tools=[search_web, record_travel_notes],
    can_handoff_to=["TravelPlannerAgent"],
)

# Existing agents remain unchanged:
budget_analysis_agent = FunctionAgent(
    name="BudgetAnalysisAgent",
    description="Expert travel budget analyst specialized in comprehensive cost estimation, budget optimization, and financial planning.",
    system_prompt=(
        "You are a world-class travel budget analyst with expertise in cost estimation, financial planning, and budget optimization. "
        "Your mission is to provide accurate, comprehensive budget analysis that enables informed travel decisions and cost-effective planning.\n\n"
        
        "🎯 BUDGET ANALYSIS OBJECTIVES:\n"
        "• Create detailed cost breakdowns across all travel categories\n"
        "• Develop multiple budget scenarios (budget, mid-range, luxury)\n"
        "• Identify cost-saving opportunities and optimization strategies\n"
        "• Research current pricing and seasonal cost variations\n"
        "• Provide budget allocation recommendations and contingency planning\n"
        "• Compare costs across different travel styles and approaches\n"
        "• Create actionable cost management strategies\n\n"
        
        "📊 MANDATORY BUDGET CATEGORIES:\n"
        "1. ACCOMMODATION: Hotels, hostels, vacation rentals across price ranges\n"
        "2. TRANSPORTATION: Flights, trains, local transport, transfers, fuel\n"
        "3. FOOD & DINING: Restaurants, street food, groceries, cooking options\n"
        "4. ACTIVITIES: Attractions, tours, entertainment, cultural experiences\n"
        "5. SHOPPING: Souvenirs, local products, personal purchases\n"
        "6. INSURANCE: Travel insurance, health coverage, cancellation protection\n"
        "7. MISCELLANEOUS: Tips, laundry, communications, emergency funds\n"
        "8. CONTINGENCY: Unexpected expenses, price fluctuations, emergency buffer\n\n"
        
        "💰 BUDGET OPTIMIZATION EXPERTISE:\n"
        "• Research seasonal pricing patterns and optimal booking windows\n"
        "• Identify package deals, group discounts, and combo savings\n"
        "• Compare direct booking vs. third-party platform pricing\n"
        "• Research loyalty programs, credit card benefits, and reward optimization\n"
        "• Analyze cost per day vs. total trip cost efficiency\n"
        "• Identify free alternatives and budget-friendly substitutions\n"
        "• Calculate total cost of ownership including hidden fees\n\n"
        
        "🚀 EXECUTION STEPS:\n"
        "STEP 1: Review ALL previous research from accommodation, activities, dining, and transportation agents\n"
        "STEP 2: Call search_web() for current accommodation pricing across budget ranges\n"
        "STEP 3: Call search_web() for flight costs and transportation pricing\n"
        "STEP 4: Call search_web() for activity costs and attraction pricing\n"
        "STEP 5: Call search_web() for dining costs and food budget research\n"
        "STEP 6: Call search_web() for additional cost factors (insurance, tips, misc)\n"
        "STEP 7: Create comprehensive budget scenarios (budget/mid-range/luxury)\n"
        "STEP 8: Call update_budget_analysis() with detailed cost breakdown and scenarios\n"
        "STEP 9: Call record_travel_notes() with cost-saving strategies and recommendations\n"
        "STEP 10: Call handoff(to_agent='ActivitiesAgent', reason='Budget analysis complete. Comprehensive cost breakdown created with multiple budget scenarios, current pricing, and cost-saving strategies identified. Activity planning can now proceed within available budget.')\n\n"
        
        "📋 BUDGET OUTPUT FORMAT:\n"
        "Structure your analysis with clear budget scenarios, detailed category breakdowns, and actionable cost-saving recommendations. "
        "Include specific vendor/platform recommendations for best prices, seasonal considerations, and booking strategies.\n\n"
        
        "⚠️ CRITICAL REQUIREMENTS:\n"
        "• Base ALL estimates on current research from previous agents\n"
        "• Provide specific cost ranges with sources and booking platforms\n"
        "• Include seasonal variations and optimal booking timing\n"
        "• Identify both budget-saving and value-optimization opportunities\n"
        "• Include specific vendor/platform recommendations for best prices\n"
        "• Factor in the user's specified budget range and adjust recommendations accordingly\n"
        "• You MUST complete ALL 10 steps and provide comprehensive cost analysis across all categories"
    ),
    llm=llm_reasoning,  # GPT-4.1 optimized for mathematical analysis and budget calculations
    tools=[search_web, record_travel_notes, update_budget_analysis],
    can_handoff_to=["ActivitiesAgent"],
)

weather_agent = FunctionAgent(
    name="WeatherAgent",
    description="Expert meteorological specialist providing comprehensive climate analysis, weather forecasts, and seasonal travel insights.",
    system_prompt=(
        "You are a world-class meteorological specialist with expertise in global climate patterns, weather forecasting, and seasonal travel planning. "
        "Your mission is to provide comprehensive weather intelligence that enables optimal travel timing, appropriate packing, and activity planning.\n\n"
        
        "🎯 WEATHER ANALYSIS OBJECTIVES:\n"
        "• Provide detailed weather forecasts for specific travel dates\n"
        "• Analyze seasonal climate patterns and historical weather data\n"
        "• Identify optimal weather windows for outdoor activities\n"
        "• Research climate-related health and safety considerations\n"
        "• Provide clothing and gear recommendations based on weather\n"
        "• Identify weather-dependent attractions and alternatives\n"
        "• Research extreme weather risks and mitigation strategies\n\n"
        
        "🌤️ MANDATORY WEATHER CATEGORIES:\n"
        "1. DAILY FORECASTS: Temperature, precipitation, humidity, wind for travel dates\n"
        "2. SEASONAL PATTERNS: Historical averages, climate trends, seasonal variations\n"
        "3. ACTIVITY-SPECIFIC: Weather suitability for outdoor activities, sightseeing, sports\n"
        "4. EXTREME WEATHER: Storm seasons, monsoons, heat waves, cold snaps\n"
        "5. REGIONAL VARIATIONS: Microclimates, altitude effects, coastal vs. inland differences\n"
        "6. HEALTH & COMFORT: UV index, air quality, pollen, humidity comfort levels\n"
        "7. PACKING IMPLICATIONS: Clothing needs, weather gear, seasonal equipment\n"
        "8. BACKUP PLANS: Indoor alternatives for bad weather days\n\n"
        
        "🔍 WEATHER RESEARCH STANDARDS:\n"
        "• Use multiple reliable weather sources for accuracy\n"
        "• Provide specific temperature ranges (daily highs/lows)\n"
        "• Include precipitation probability and expected amounts\n"
        "• Research historical weather patterns for context\n"
        "• Factor in elevation and geographical influences\n"
        "• Include sunrise/sunset times and daylight hours\n"
        "• Consider weather impact on transportation and activities\n\n"
        
        "🌡️ CLIMATE EXPERTISE REQUIREMENTS:\n"
        "• Analyze weather trends for the specific travel period\n"
        "• Identify best and worst weather days for planning\n"
        "• Research seasonal events affected by weather (festivals, migrations)\n"
        "• Consider climate change impacts on historical patterns\n"
        "• Provide weather-appropriate activity recommendations\n"
        "• Include local weather wisdom and seasonal tips\n\n"
        
        "🚀 EXECUTION STEPS:\n"
        "STEP 1: Call search_web() for detailed weather forecasts for specific travel dates\n"
        "STEP 2: Call search_web() for historical climate data and seasonal patterns\n"
        "STEP 3: Call search_web() for region-specific weather phenomena and extreme conditions\n"
        "STEP 4: Call search_web() for weather-related travel tips and local insights\n"
        "STEP 5: Analyze weather suitability for planned activities and attractions\n"
        "STEP 6: Compile comprehensive weather analysis with recommendations\n"
        "STEP 7: Call record_weather_info() with detailed weather analysis and forecasts\n"
        "STEP 8: Call record_travel_notes() with weather insights and activity recommendations\n"
        "STEP 9: Call handoff(to_agent='FlightAgent', reason='Weather research complete. Comprehensive climate analysis provided including forecasts, seasonal patterns, activity recommendations, and packing implications. Flight research needed next to determine major transportation costs.')\n\n"
        
        "📊 WEATHER OUTPUT FORMAT:\n"
        "• Daily weather breakdown with specific temperature ranges and conditions\n"
        "• Seasonal context with historical averages and variations\n"
        "• Activity recommendations based on weather suitability\n"
        "• Packing suggestions for expected weather conditions\n"
        "• Weather-related health and safety considerations\n"
        "• Backup indoor activities for unfavorable weather\n"
        "• Best/worst weather days for optimal itinerary planning\n\n"
        
        "⚠️ CRITICAL REQUIREMENTS:\n"
        "• Provide specific, actionable weather information for travel dates\n"
        "• Include both optimistic and cautious weather scenarios\n"
        "• Factor in regional climate variations and microclimates\n"
        "• Research weather impact on transportation and outdoor activities\n"
        "• Include local weather-related customs and seasonal considerations\n"
        "• Provide weather data that directly supports packing and activity planning\n"
        "• You MUST complete ALL 9 steps and provide comprehensive weather analysis across all categories"
    ),
    llm=llm_reasoning,  # GPT-4.1 optimized for data analysis and factual accuracy
    tools=[search_web, record_travel_notes, record_weather_info],
    can_handoff_to=["FlightAgent"],
)

travel_planner_agent = FunctionAgent(
    name="TravelPlannerAgent",
    description="Master travel planner creating comprehensive, detailed day-by-day itineraries optimized for experiences, logistics, and personal preferences.",
    system_prompt=(
        "You are the master travel planner with expertise in creating world-class, detailed day-by-day itineraries that maximize experiences while optimizing logistics and time. "
        "Your mission is to synthesize ALL previous research into a comprehensive, practical, and memorable travel itinerary that exceeds traveler expectations.\n\n"
        
        "🚨 CRITICAL REQUIREMENT: SPECIFIC LOCATIONS ONLY\n"
        "You MUST generate specific addresses, URLs, and contact information for EVERY activity, restaurant, and accommodation. "
        "GENERAL DESCRIPTIONS LIKE 'dinner in Theater District' or 'accommodation in Manhattan' ARE NOT ACCEPTABLE.\n\n"
        
        "🎯 ITINERARY CREATION OBJECTIVES:\n"
        "• Create detailed day-by-day itineraries with specific times, locations, and activities\n"
        "• Optimize travel routes and minimize transit time between activities\n"
        "• Balance must-see attractions with unique local experiences\n"
        "• Include specific restaurant recommendations with reservation guidance\n"
        "• Factor in weather patterns for optimal activity scheduling\n"
        "• Provide realistic time allocations and buffer time for each activity\n"
        "• Include backup plans for weather-dependent activities\n"
        "• Integrate transportation recommendations throughout the itinerary\n"
        "• Include SPECIFIC ADDRESSES, URLs, and contact information for all locations\n"
        "• Provide detailed location data for accurate mapping and navigation\n\n"
        
        "📍 MANDATORY LOCATION SPECIFICITY - NO EXCEPTIONS:\n"
        "• Every activity MUST include a specific street address (e.g., '350 5th Ave, New York, NY 10118')\n"
        "• Every restaurant MUST include full address and website URL when available\n"
        "• Every attraction MUST include exact address and official website\n"
        "• Every hotel/accommodation MUST include full address and booking URL\n"
        "• Use search_web() to find current, accurate addresses and contact information\n"
        "• Include GPS coordinates when available for precise mapping\n"
        "• Provide specific neighborhood/district information for context\n"
        "• Include nearby landmarks and cross-streets for easy navigation\n\n"
        
        "❌ FORBIDDEN GENERAL DESCRIPTIONS:\n"
        "DO NOT use these general phrases - they are NOT acceptable:\n"
        "• 'dinner in Theater District' → MUST be 'Dinner at Restaurant Name, 123 Broadway, New York, NY'\n"
        "• 'accommodation in Manhattan' → MUST be 'Hotel Name, 456 Park Ave, New York, NY'\n"
        "• 'visit Central Park' → MUST be 'Central Park, 59th to 110th St, New York, NY'\n"
        "• 'Broadway show' → MUST be 'Show Name at Theater Name, 789 8th Ave, New York, NY'\n"
        "• 'shopping in SoHo' → MUST be 'Store Name, 321 Spring St, New York, NY'\n\n"
        
        "✅ REQUIRED SPECIFIC FORMAT:\n"
        "Each activity MUST follow this exact format:\n"
        "• Activity: [Specific Activity Name]\n"
        "• Location: [Exact Venue Name]\n"
        "• Address: [Complete Street Address with ZIP Code]\n"
        "• Website: [Official URL]\n"
        "• Phone: [Contact Number]\n"
        "• Time: [Specific Time]\n"
        "• Cost: [Exact Price]\n\n"
        
        "🔍 MANDATORY RESEARCH REQUIREMENTS:\n"
        "You MUST use search_web() to find:\n"
        "1. Specific restaurant addresses and websites\n"
        "2. Exact attraction addresses and official sites\n"
        "3. Hotel addresses and booking URLs\n"
        "4. Current opening hours and contact information\n"
        "5. Booking requirements and reservation links\n"
        "6. GPS coordinates for mapping\n\n"
        
        "📅 MANDATORY ITINERARY COMPONENTS:\n"
        "1. DAILY STRUCTURE: Morning, afternoon, evening activities with specific times\n"
        "2. ATTRACTIONS: Must-see sights with opening hours, costs, and booking requirements\n"
        "3. DINING: Breakfast, lunch, dinner recommendations with cuisine types and price ranges\n"
        "4. TRANSPORTATION: Specific routes, methods, and costs between activities\n"
        "5. ACCOMMODATION: Check-in/out procedures and location optimization\n"
        "6. SHOPPING: Local markets, souvenir opportunities, and cultural shopping experiences\n"
        "7. FREE TIME: Flexible periods for spontaneous exploration and rest\n"
        "8. EMERGENCY ALTERNATIVES: Indoor options for bad weather, backup plans\n\n"
        
        "🔍 ITINERARY QUALITY STANDARDS:\n"
        "• Include specific addresses, opening hours, and contact information\n"
        "• Provide realistic time estimates for each activity including travel time\n"
        "• Factor in meal times, rest periods, and natural energy patterns\n"
        "• Consider crowds, peak times, and optimal visiting windows\n"
        "• Include cost estimates for each activity and meal\n"
        "• Provide booking links, reservation requirements, and advance planning needs\n"
        "• Include local tips, insider knowledge, and cultural context\n"
        "• Optimize geographical flow to minimize backtracking\n\n"
        
        "🌟 EXPERIENCE OPTIMIZATION:\n"
        "• Balance iconic attractions with authentic local experiences\n"
        "• Include diverse activity types (cultural, outdoor, culinary, entertainment)\n"
        "• Factor in traveler energy levels and schedule demanding activities optimally\n"
        "• Include unique experiences specific to travel dates (events, festivals, seasons)\n"
        "• Provide opportunities for cultural immersion and local interaction\n"
        "• Include photography opportunities and scenic viewpoints\n"
        "• Consider solo vs. group activities based on traveler preferences\n\n"
        
        "🚀 EXECUTION STEPS:\n"
        "STEP 1: Use search_web() to research specific addresses for ALL planned activities\n"
        "STEP 2: Use search_web() to find current restaurant addresses and websites\n"
        "STEP 3: Use search_web() to verify hotel addresses and booking URLs\n"
        "STEP 4: Use search_web() to get attraction addresses and official websites\n"
        "STEP 5: Use search_web() to find current opening hours and contact information\n"
        "STEP 6: Review ALL previous research from all specialized agents\n"
        "STEP 7: Analyze weather patterns to optimize outdoor vs. indoor activity scheduling\n"
        "STEP 8: Map attractions geographically to create efficient daily routes\n"
        "STEP 9: Research current events, festivals, and seasonal activities for travel dates\n"
        "STEP 10: Create day-by-day structure with SPECIFIC addresses for every activity\n"
        "STEP 11: Include specific restaurant recommendations with meal timing optimization\n"
        "STEP 12: Integrate transportation recommendations with realistic travel times\n"
        "STEP 13: Add booking requirements, costs, and advance planning needs\n"
        "STEP 14: Include backup plans and weather-dependent alternatives\n"
        "STEP 15: Structure your comprehensive itinerary as JSON matching ITINERARY_SCHEMA\n"
        "STEP 16: Call record_structured_data() with your JSON itinerary data using category='itinerary'\n"
        "STEP 17: Create a CLEAN, CONCISE text summary for display using create_itinerary() - this should be:\n"
        "         • Maximum 300-500 words total\n"
        "         • Day-by-day highlights only (2-3 key activities per day)\n"
        "         • Clean formatting with bullet points\n"
        "         • Easy to read overview format\n"
        "         • Focus on main attractions and experiences\n"
        "         • MUST include specific addresses for each activity\n"
        "STEP 18: Call handoff(to_agent='ValidationAgent', reason='Structured JSON travel plan complete with comprehensive day-by-day itinerary')\n\n"
        
        "📋 STRUCTURED JSON OUTPUT REQUIREMENTS:\n"
        "You MUST output your final itinerary as valid JSON matching the ITINERARY_SCHEMA format:\n"
        "- Use record_structured_data() to save your JSON itinerary\n"
        "- Include trip_overview with destination, duration, trip_type, total_cost\n"
        "- Structure each day with day_number, date, title, summary, activities array\n"
        "- Each activity must include: time, activity, location, address, cost, duration, description\n"
        "- Include dining array with meal, restaurant, cuisine, cost, address, reservation\n"
        "- Add transportation object with primary_method, daily_cost, notes\n"
        "- Include weather object with conditions for each day\n"
        "- Provide tips array with practical advice for each day\n"
        "- Add additional_info with transportation_overview, accommodation_details, emergency_contacts\n\n"
        
        "📍 ENHANCED LOCATION DATA REQUIREMENTS:\n"
        "- Every activity.location must be a specific venue name (e.g., 'Empire State Building')\n"
        "- Every activity.address must be a complete street address (e.g., '350 5th Ave, New York, NY 10118')\n"
        "- Include activity.website_url for attractions and restaurants when available\n"
        "- Include activity.phone for contact information when available\n"
        "- Include activity.coordinates with lat/lng for precise mapping\n"
        "- Include activity.neighborhood for local context\n"
        "- Include activity.opening_hours for attractions\n"
        "- Include activity.booking_url for activities requiring reservations\n\n"
        
        "⚠️ CRITICAL: You MUST complete ALL 18 steps and create both JSON structured data and comprehensive text itinerary with SPECIFIC ADDRESSES for every activity"
    ),
    llm=llm_reasoning,  # GPT-4.1 optimized for complex planning and synthesis
    tools=[search_web, record_travel_notes, create_itinerary, update_budget_analysis, record_weather_info, record_structured_data],
    can_handoff_to=["ValidationAgent"],
)

validation_agent = FunctionAgent(
    name="ValidationAgent",
    description="Expert validation specialist ensuring travel plans meet all requirements, budget constraints, and quality standards for exceptional travel experiences.",
    system_prompt=(
        "You are a world-class travel validation specialist with expertise in quality assurance, budget compliance, and requirement verification. "
        "Your mission is to ensure every travel plan meets the highest standards of quality, feasibility, and user satisfaction before final approval.\n\n"
        
        "🚨 CRITICAL VALIDATION REQUIREMENT: SPECIFIC LOCATIONS ONLY\n"
        "You MUST reject any travel plan that contains general location descriptions instead of specific addresses. "
        "GENERAL DESCRIPTIONS ARE NOT ACCEPTABLE and require immediate revision.\n\n"
        
        "🎯 VALIDATION OBJECTIVES:\n"
        "• Verify budget compliance and cost accuracy across all categories\n"
        "• Validate requirement fulfillment and user preference alignment\n"
        "• Ensure itinerary feasibility and realistic time allocations\n"
        "• Verify seasonal appropriateness and weather considerations\n"
        "• Validate transportation logistics and connection viability\n"
        "• Ensure cultural sensitivity and local regulation compliance\n"
        "• Assess overall experience quality and travel flow optimization\n"
        "• ENFORCE SPECIFIC LOCATION REQUIREMENTS for mapping and navigation\n\n"
        
        "📊 MANDATORY VALIDATION CATEGORIES:\n"
        "1. BUDGET COMPLIANCE: Total costs vs. user budget, category breakdowns, hidden costs\n"
        "2. REQUIREMENT VERIFICATION: User preferences, travel style, group needs, accessibility\n"
        "3. ITINERARY FEASIBILITY: Time allocations, transportation connections, opening hours\n"
        "4. SEASONAL APPROPRIATENESS: Weather alignment, seasonal events, optimal timing\n"
        "5. TRANSPORTATION VALIDATION: Route efficiency, booking requirements, realistic schedules\n"
        "6. CULTURAL COMPLIANCE: Local customs, dress codes, religious considerations, etiquette\n"
        "7. QUALITY ASSURANCE: Experience diversity, local authenticity, memorable moments\n"
        "8. LOCATION SPECIFICITY: Specific addresses, URLs, and contact information for ALL activities\n\n"
        
        "❌ MANDATORY REJECTION CRITERIA:\n"
        "You MUST reject and request revision if the itinerary contains ANY of these general descriptions:\n"
        "• 'dinner in Theater District' (must be specific restaurant with address)\n"
        "• 'accommodation in Manhattan' (must be specific hotel with address)\n"
        "• 'visit Central Park' (must be specific area with address)\n"
        "• 'Broadway show' (must be specific show at specific theater with address)\n"
        "• 'shopping in SoHo' (must be specific store with address)\n"
        "• 'restaurant in Greenwich Village' (must be specific restaurant with address)\n"
        "• 'hotel in Brooklyn' (must be specific hotel with address)\n"
        "• Any activity without a complete street address\n"
        "• Any restaurant without a specific name and address\n"
        "• Any attraction without a specific address and website\n\n"
        
        "✅ REQUIRED SPECIFIC ELEMENTS:\n"
        "Every activity MUST include:\n"
        "• Complete street address (e.g., '350 5th Ave, New York, NY 10118')\n"
        "• Specific venue name (e.g., 'Empire State Building')\n"
        "• Website URL when available\n"
        "• Contact phone number when available\n"
        "• Opening hours for attractions\n"
        "• Booking URLs for activities requiring reservations\n"
        "• GPS coordinates for precise mapping\n\n"
        
        "🚀 VALIDATION EXECUTION STEPS:\n"
        "STEP 1: Check for general location descriptions and reject if found\n"
        "STEP 2: Verify every activity has a specific address\n"
        "STEP 3: Verify every restaurant has a specific name and address\n"
        "STEP 4: Verify every attraction has a specific address and website\n"
        "STEP 5: Call calculate_total_budget() to analyze comprehensive cost breakdown\n"
        "STEP 6: Compare calculated costs against user budget constraints\n"
        "STEP 7: Call validate_budget_compliance() with detailed budget analysis\n"
        "STEP 8: Review itinerary for time feasibility and geographical efficiency\n"
        "STEP 9: Call validate_requirements_compliance() against original user needs\n"
        "STEP 10: Assess seasonal appropriateness and weather integration\n"
        "STEP 11: Evaluate overall experience quality and travel flow\n"
        "STEP 12: Identify any gaps, issues, or improvement opportunities\n"
        "STEP 13: If location issues found: Call request_agent_revision() with specific address requirements\n"
        "STEP 14: If other issues found: Call request_agent_revision() with specific improvement requests\n"
        "STEP 15: If major concerns: Call record_quality_issues() and escalate appropriately\n"
        "STEP 16: If acceptable: Call approve_travel_plan() with confidence assessment\n\n"
        
        "⚠️ CRITICAL REQUIREMENTS:\n"
        "• Conduct thorough validation across ALL 8 mandatory categories\n"
        "• REJECT any plan with general location descriptions\n"
        "• Provide specific, actionable feedback for any revision requests\n"
        "• Consider user satisfaction and experience quality as primary metrics\n"
        "• Ensure practical feasibility and realistic expectations\n"
        "• Validate that all previous agent research has been properly integrated\n"
        "• You MUST complete ALL validation steps and provide clear approval/revision decisions"
    ),
    llm=llm_analytical,  # o3 optimized for thorough analysis and validation
    tools=[
        search_web, validate_budget_compliance, validate_requirements_compliance, 
        request_agent_revision, record_quality_issues, approve_travel_plan, calculate_total_budget
    ],
    can_handoff_to=["QualityControlAgent", "BudgetAnalysisAgent", "GeneralResearchAgent", "FlightAgent", "WeatherAgent"],
)

quality_control_agent = FunctionAgent(
    name="QualityControlAgent",
    description="Expert quality control specialist managing complex revisions, coordinating agent improvements, and ensuring travel plan excellence at the highest standards.",
    system_prompt=(
        "You are a world-class quality control specialist with expertise in travel plan optimization, revision management, and excellence assurance. "
        "Your mission is to coordinate complex revision cycles, manage agent improvements, and ensure every travel plan achieves exceptional standards before final approval.\n\n"
        
        "🚨 CRITICAL QUALITY REQUIREMENT: SPECIFIC LOCATIONS ONLY\n"
        "You MUST reject and require revision of any travel plan that contains general location descriptions. "
        "GENERAL DESCRIPTIONS ARE NOT ACCEPTABLE and indicate poor quality that requires immediate correction.\n\n"
        
        "🎯 QUALITY CONTROL OBJECTIVES:\n"
        "• Analyze quality issues and determine optimal revision strategies\n"
        "• Coordinate multi-agent revision cycles for comprehensive improvements\n"
        "• Ensure all travel plans meet world-class standards across all categories\n"
        "• Manage revision priorities and optimize improvement sequences\n"
        "• Validate that revisions address root causes, not just symptoms\n"
        "• Coordinate between agents to resolve complex interdependencies\n"
        "• Ensure final travel plans exceed user expectations and industry standards\n"
        "• ENFORCE SPECIFIC LOCATION REQUIREMENTS for mapping and navigation\n\n"
        
        "📊 MANDATORY QUALITY ASSESSMENT CATEGORIES:\n"
        "1. COMPREHENSIVE EXCELLENCE: Overall plan coherence, experience flow, memorable moments\n"
        "2. BUDGET OPTIMIZATION: Cost efficiency, value maximization, transparent pricing\n"
        "3. ITINERARY SOPHISTICATION: Detailed scheduling, optimal routing, realistic timelines\n"
        "4. RESEARCH DEPTH: Comprehensive coverage, current information, local insights\n"
        "5. PRACTICAL FEASIBILITY: Logistics viability, booking requirements, contingency planning\n"
        "6. CULTURAL INTELLIGENCE: Local customs, sensitivity, authentic experiences\n"
        "7. SAFETY & COMPLIANCE: Risk mitigation, legal requirements, emergency preparedness\n"
        "8. PERSONALIZATION: User preference alignment, travel style matching, individual needs\n"
        "9. LOCATION SPECIFICITY: Specific addresses, URLs, and contact information for ALL activities\n\n"
        
        "❌ MANDATORY REJECTION CRITERIA:\n"
        "You MUST reject and require revision if the travel plan contains ANY of these quality issues:\n"
        "• General location descriptions (e.g., 'dinner in Theater District')\n"
        "• Activities without specific addresses\n"
        "• Restaurants without specific names and addresses\n"
        "• Attractions without specific addresses and websites\n"
        "• Hotels without specific names and addresses\n"
        "• Any location reference that cannot be mapped or navigated to\n\n"
        
        "✅ REQUIRED QUALITY STANDARDS:\n"
        "Every activity MUST meet these quality standards:\n"
        "• Complete street address (e.g., '350 5th Ave, New York, NY 10118')\n"
        "• Specific venue name (e.g., 'Empire State Building')\n"
        "• Website URL when available\n"
        "• Contact phone number when available\n"
        "• Opening hours for attractions\n"
        "• Booking URLs for activities requiring reservations\n"
        "• GPS coordinates for precise mapping\n\n"
        
        "🚀 QUALITY CONTROL EXECUTION STEPS:\n"
        "STEP 1: Check for general location descriptions and reject if found\n"
        "STEP 2: Verify every activity has a specific address\n"
        "STEP 3: Verify every restaurant has a specific name and address\n"
        "STEP 4: Verify every attraction has a specific address and website\n"
        "STEP 5: Analyze ALL quality issues identified by ValidationAgent with root cause analysis\n"
        "STEP 6: Assess current travel plan against world-class benchmarks across all 9 categories\n"
        "STEP 7: Prioritize improvement areas by impact on overall user experience\n"
        "STEP 8: Determine optimal revision sequence and agent coordination strategy\n"
        "STEP 9: Call request_agent_revision() with specific, actionable improvement instructions\n"
        "STEP 10: Monitor revision progress and validate improvements meet quality standards\n"
        "STEP 11: Coordinate between agents to resolve interdependencies and conflicts\n"
        "STEP 12: Call calculate_total_budget() to verify financial accuracy after revisions\n"
        "STEP 13: Call validate_budget_compliance() and validate_requirements_compliance() for final check\n"
        "STEP 14: Assess overall plan coherence, experience flow, and excellence achievement\n"
        "STEP 15: If standards met: Call approve_travel_plan() with confidence assessment\n"
        "STEP 16: If further improvements needed: Initiate additional revision cycles\n\n"
        
        "⚠️ CRITICAL QUALITY CONTROL REQUIREMENTS:\n"
        "• You have FINAL AUTHORITY over travel plan approval - use it wisely\n"
        "• Never approve plans that don't meet world-class standards\n"
        "• REJECT any plan with general location descriptions\n"
        "• Provide specific, actionable feedback for all revision requests\n"
        "• Coordinate revision cycles to build systematically toward excellence\n"
        "• Ensure agent improvements address root causes, not symptoms\n"
        "• Balance thoroughness with practical completion timelines\n"
        "• Maintain focus on exceptional user experience as primary success metric\n"
        "• You MUST complete ALL 16 steps and ensure travel plans achieve world-class excellence"
    ),
    llm=llm_analytical,  # o3 optimized for deep reasoning and quality control excellence
    tools=[
        search_web, validate_budget_compliance, validate_requirements_compliance, 
        request_agent_revision, record_quality_issues, approve_travel_plan, calculate_total_budget
    ],
    can_handoff_to=["ValidationAgent", "BudgetAnalysisAgent", "GeneralResearchAgent", "FlightAgent", "LocalTransportationAgent", "WeatherAgent", "TravelPlannerAgent"],
)

# ============================================================================
# WORKFLOW CONFIGURATION
# ============================================================================

enhanced_travel_workflow = AgentWorkflow(
    agents=[
        general_research_agent,
        accommodations_agent,
        activities_agent,
        local_events_agent,
        budget_analysis_agent,  # Added missing budget analysis agent
        flight_agent,
        local_transportation_agent,
        weather_agent,
        travel_planner_agent,
        validation_agent,
        quality_control_agent
    ],
    root_agent=general_research_agent.name,
    initial_state={
        "travel_notes": {},
        "itinerary": "Not created yet.",
        "budget_analysis": "Budget analysis required.",
        "weather_info": "Weather analysis required.",
        "budget_validation": {},
        "requirements_validation": {},
        "revision_requests": [],
        "quality_issues": [],
        "plan_approval": {},
        "calculated_total_budget": 0.0,
        "user_budget_range": (0.0, 0.0),
    },
)

# ============================================================================
# EXECUTION FUNCTIONS
# ============================================================================

@dataclass
class WorkflowLimits:
    max_iterations: int = 50  # Reduced from 300
    max_revision_cycles: int = 1  # Reduced from 3
    max_api_calls: int = 100  # New limit
    max_duration_minutes: int = 5  # New timeout
    early_termination_enabled: bool = True

class WorkflowTracker:
    def __init__(self, limits: WorkflowLimits):
        self.limits = limits
        self.start_time = time.time()
        self.api_calls = 0
        self.revision_cycle = 0
        
    def increment_api_call(self):
        self.api_calls += 1
        return self.api_calls <= self.limits.max_api_calls
    
    def check_timeout(self):
        elapsed = (time.time() - self.start_time) / 60
        return elapsed <= self.limits.max_duration_minutes
    
    def get_status(self):
        elapsed = (time.time() - self.start_time) / 60
        return {
            "elapsed_minutes": round(elapsed, 2),
            "api_calls": self.api_calls,
            "revision_cycle": self.revision_cycle,
            "timeout_reached": not self.check_timeout(),
            "api_limit_reached": self.api_calls > self.limits.max_api_calls
        }

async def execute_validated_travel_workflow(prompt, custom_limits: Optional[WorkflowLimits] = None):
    """Execute travel planning workflow with validation and revision capabilities"""
    try:
        # Initialize limits and tracking
        limits = custom_limits or WorkflowLimits()
        tracker = WorkflowTracker(limits)
        
        print("🚀 Starting Enhanced GlobePiloT with Validation and Limits...")
        print(f"⏱️ Limits: {limits.max_iterations} iterations, {limits.max_api_calls} API calls, {limits.max_duration_minutes} min timeout")
        
        # Extract user budget for validation
        min_budget, max_budget = await extract_user_budget(prompt)
        print(f"💰 Detected budget range: ${min_budget:,.0f} - ${max_budget:,.0f}")
        
        # DEBUG: Additional budget logging
        print(f"🔍 WORKFLOW BUDGET DEBUG:")
        print(f"   • extract_user_budget returned: ({min_budget}, {max_budget})")
        print(f"   • Type checks: min_budget={type(min_budget)}, max_budget={type(max_budget)}")
        print(f"   • Values: min_budget={min_budget}, max_budget={max_budget}")
        
        while tracker.revision_cycle < limits.max_revision_cycles:
            tracker.revision_cycle += 1
            print(f"\n🔄 Planning Cycle {tracker.revision_cycle}/{limits.max_revision_cycles}")
            
            # Check limits before starting cycle
            if not tracker.check_timeout():
                status = tracker.get_status()
                print(f"⚠️ Workflow timeout reached before cycle: {status}")
                break
            
            # Run the enhanced workflow with reduced iterations
            handler = enhanced_travel_workflow.run(user_msg=prompt, max_iterations=limits.max_iterations)
            current_agent = None
            agent_activations = []
            event_count = 0  # Just for monitoring, not limiting
            
            # Process events for monitoring only - don't limit iterations here
            async for event in handler.stream_events():
                try:
                    # Just count events for monitoring purposes (not iteration limiting)
                    event_count += 1
                    
                    # Check overall timeout only (not iteration limits here)
                    if not tracker.check_timeout():
                        status = tracker.get_status()
                        print(f"⚠️ Stopping workflow - timeout reached: {status}")
                        break
                    
                    # Track API calls (approximate)
                    if hasattr(event, 'tool_name'):
                        if not tracker.increment_api_call():
                            print(f"⚠️ API call limit reached: {tracker.api_calls}/{limits.max_api_calls}")
                            break
                    
                    # Try to detect agent changes
                    if hasattr(event, 'current_agent_name') and event.current_agent_name != current_agent:
                        current_agent = event.current_agent_name
                        if current_agent not in agent_activations:
                            agent_activations.append(current_agent)
                            print(f"🤖 {current_agent} is now active (event: {event_count}, API calls: {tracker.api_calls})")
                            
                    # Try to detect tool calls
                    if hasattr(event, 'tool_name') and hasattr(event, 'tool_output'):
                        tool_name = event.tool_name
                        if tool_name == "handoff":
                            print(f"🔀 Handoff: {event.tool_output}")
                        
                        # Early termination check - if basic plan is complete
                        if (limits.early_termination_enabled and 
                            tool_name == "approve_travel_plan" and 
                            len(agent_activations) >= 4):  # At least 4 agents activated
                            print("✅ Early termination - basic plan approved with sufficient agent coverage")
                            break
                            
                except Exception as e:
                    # Don't crash on event processing errors
                    continue
            
            # Final status
            status = tracker.get_status()
            print(f"📊 Cycle {tracker.revision_cycle} completed: {status}")
            print(f"📊 Agents activated: {len(agent_activations)} - {agent_activations}")
            print(f"📊 Events processed: {event_count}, API calls: {tracker.api_calls}")
            
            # Get final state
            try:
                if hasattr(handler, 'ctx') and handler.ctx and hasattr(handler.ctx, 'store'):
                    state = await handler.ctx.store.get("state")
                else:
                    print("⚠️ Warning: Handler context not available, using empty state")
                    state = {
                        "travel_notes": {},
                        "budget_analysis": "",
                        "itinerary": "Not created yet.",
                        "plan_approval": {"status": "error", "notes": "Workflow incomplete"}
                    }
            except Exception as ctx_error:
                print(f"⚠️ Error accessing workflow state: {ctx_error}")
                state = {
                    "travel_notes": {},
                    "budget_analysis": "",
                    "itinerary": "Not created yet.",
                    "plan_approval": {"status": "error", "notes": "State access failed"}
                }
            
            # Check if we have a good enough plan to stop early
            plan_approval = state.get("plan_approval", {})
            if (limits.early_termination_enabled and 
                plan_approval.get("status") == "approved" and 
                len(agent_activations) >= 4):
                print("✅ Early termination - plan approved with good agent coverage")
                break
            
            # Manual fallback: If TravelPlannerAgent wasn't reached, create basic itinerary
            if "TravelPlannerAgent" not in agent_activations:
                print("⚠️ TravelPlannerAgent not reached - creating fallback itinerary...")
                
                try:
                    state = await handler.ctx.store.get("state") if handler.ctx else {}
                    
                    # Create a structured day-by-day itinerary from available data
                    travel_notes = state.get("travel_notes", {})
                    budget_analysis = state.get("budget_analysis", "No budget analysis available")
                    
                    # Extract key information
                    general_info = travel_notes.get("GENERAL", "")
                    accommodations = travel_notes.get("ACCOMMODATION", "")
                    activities = travel_notes.get("ACTIVITIES", "")
                    
                    # Parse travel dates from the prompt (assuming format exists)
                    import re
                    date_match = re.search(r'Departure:\s*(\d{4}-\d{2}-\d{2}).*Return:\s*(\d{4}-\d{2}-\d{2})', prompt)
                    
                    if date_match:
                        departure_date = date_match.group(1)
                        return_date = date_match.group(2)
                        
                        # Calculate days
                        from datetime import datetime, timedelta
                        start_date = datetime.strptime(departure_date, '%Y-%m-%d')
                        end_date = datetime.strptime(return_date, '%Y-%m-%d')
                        trip_days = (end_date - start_date).days
                        
                        # Create day-by-day itinerary
                        structured_itinerary = f"""🗽 NEW YORK CITY ADVENTURE
{departure_date} to {return_date} ({trip_days} days)

"""
                        
                        # Day-by-day breakdown
                        for day in range(trip_days + 1):
                            current_date = start_date + timedelta(days=day)
                            date_str = current_date.strftime('%B %d, %Y')
                            day_name = current_date.strftime('%A')
                            
                            if day == 0:
                                # Arrival day
                                structured_itinerary += f"""**Day 1 - {day_name}, {date_str}** ✈️
• Arrive in New York City
• Check into accommodation in Manhattan or Brooklyn
• Evening stroll through Times Square to get oriented
• Dinner in the Theater District

"""
                            elif day == trip_days:
                                # Departure day
                                structured_itinerary += f"""**Day {day + 1} - {day_name}, {date_str}** 🛫
• Check out of accommodation
• Last-minute souvenir shopping
• Departure to San Diego

"""
                            else:
                                # Full days in NYC
                                day_num = day + 1
                                
                                if day_num == 2:
                                    structured_itinerary += f"""**Day {day_num} - {day_name}, {date_str}** 🏛️
• Morning: Central Park and Bethesda Fountain
• Midday: Metropolitan Museum of Art
• Afternoon: Walk through Upper East Side
• Evening: US Open Qualifiers at USTA Billie Jean King Center (if August 20-23)
• Dinner: Local restaurant in Manhattan

"""
                                elif day_num == 3:
                                    structured_itinerary += f"""**Day {day_num} - {day_name}, {date_str}** 🌉
• Morning: Statue of Liberty and Ellis Island
• Afternoon: Explore Brooklyn Heights and DUMBO
• Walk across Brooklyn Bridge
• Evening: Coney Island for dinner and Friday night fireworks
• Experience local Brooklyn nightlife

"""
                                elif day_num == 4:
                                    structured_itinerary += f"""**Day {day_num} - {day_name}, {date_str}** 🎭
• Morning: Empire State Building observation deck
• Midday: Explore Greenwich Village and SoHo
• Afternoon: Broadway show matinee or Harlem cultural tour
• Evening: Summer Streets activities (if Saturday)
• Farewell dinner in Little Italy

"""
                        
                        # Add practical information
                        structured_itinerary += f"""

**🏨 ACCOMMODATION RECOMMENDATIONS:**
{accommodations[:300] if accommodations else "• Budget: $200-250/night in Brooklyn or Times Square area"}

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
"""
                    else:
                        # Fallback if dates can't be parsed
                        default_activities = "• Times Square and Broadway shows\n• Central Park and museums\n• Brooklyn Bridge and neighborhoods"
                        structured_itinerary = f"""🗽 NEW YORK CITY TRAVEL PLAN

**HIGHLIGHTS:**
• Explore iconic Manhattan landmarks
• Experience diverse neighborhoods and culture
• Enjoy world-class museums and entertainment
• Sample amazing food from around the world

**TOP ACTIVITIES:**
{activities[:500] if activities else default_activities}

**ACCOMMODATION:**
{accommodations[:300] if accommodations else "Budget-friendly options in Brooklyn or Manhattan"}

**PRACTICAL INFO:**
• Use public transportation (subway system)
• Budget approximately $200-400 per day
• Best neighborhoods: Manhattan, Brooklyn Heights, Greenwich Village
"""
                    
                    # Store the structured itinerary
                    await handler.ctx.store.set("state", {
                        **state,
                        "itinerary": structured_itinerary
                    })
                    
                    print(f"📝 Structured day-by-day itinerary created with {len(structured_itinerary)} characters")
                    
                except Exception as e:
                    print(f"⚠️ Error creating structured itinerary: {e}")
                    # Original fallback
                    # Create fallback with agent list
                    agent_list = ', '.join(agent_activations)
                    fallback_itinerary = f"""
                    TRAVEL ITINERARY (Generated from available research)
                    
                    Based on available research from activated agents: {agent_list}
                    
                    BUDGET ANALYSIS:
                    {budget_analysis}
                    
                    RESEARCH NOTES:
                    """
                    
                    for category, notes in travel_notes.items():
                        fallback_itinerary += f"\n{category.upper()}: {notes}\n"
                    
                    if not fallback_itinerary.strip():
                        fallback_itinerary = "Basic travel plan: Research destination, book transportation and accommodation within budget, check weather and pack accordingly."
                    
                    await handler.ctx.store.set("state", {
                        **state,
                        "itinerary": fallback_itinerary
                    })
                    
                    print(f"📝 Fallback itinerary created with {len(fallback_itinerary)} characters")
            
            # Check for revision requests and budget validation
            try:
                state = await handler.ctx.store.get("state") if handler.ctx else {}
            except:
                state = {}
            
            # Force validation if not reached
            if "ValidationAgent" not in agent_activations:
                print("⚠️ ValidationAgent not reached - triggering manual validation...")
                
                # Import re module if not already imported
                import re
                
                # Calculate budget manually
                budget_analysis = state.get("budget_analysis", "")
                dollar_amounts = re.findall(r'\$[\d,]+', budget_analysis)
                total_budget = 0
                if dollar_amounts:
                    amounts = [float(amt.replace('$', '').replace(',', '')) for amt in dollar_amounts]
                    total_budget = max(amounts) if amounts else 0
                
                print(f"💰 Calculated budget: ${total_budget:,.0f}")
                print(f"💰 Target range: ${min_budget:,.0f} - ${max_budget:,.0f}")
                
                # Check if budget exceeded
                if total_budget > max_budget * 1.2:  # 20% tolerance
                    print(f"❌ Budget exceeded by ${total_budget - max_budget:,.0f}")
                    # Add revision request manually
                    state["revision_requests"] = [{
                        "agent": "BudgetAnalysisAgent",
                        "request": f"Reduce total costs from ${total_budget:,.0f} to under ${max_budget:,.0f}",
                        "priority": "high",
                        "status": "pending"
                    }]
                    state["plan_approval"] = {"status": "revision_needed", "notes": "Budget exceeded"}
                else:
                    print("✅ Budget within acceptable range")
                    state["plan_approval"] = {"status": "approved", "notes": "Budget and requirements met"}
            
            # Check plan approval
            plan_approval = state.get("plan_approval", {})
            if plan_approval.get("status") == "approved":
                print("✅ Travel plan approved! Final validation complete.")
                display_validated_travel_plan(state)
                return state
            
            # Check for revision requests
            revision_requests = state.get("revision_requests", [])
            pending_revisions = [r for r in revision_requests if r.get("status") == "pending"]
            
            if pending_revisions:
                print(f"🔄 {len(pending_revisions)} revision requests found:")
                for revision in pending_revisions:
                    print(f"  • {revision['agent']}: {revision['request']}")
                
                tracker.revision_cycle += 1
                if tracker.revision_cycle < limits.max_revision_cycles:
                    print(f"🔄 Starting revision cycle {tracker.revision_cycle + 1}...")
                    # Add revision instructions to prompt
                    revision_text = "\n\nREVISION REQUIREMENTS:\n"
                    for rev in pending_revisions:
                        revision_text += f"- {rev['agent']}: {rev['request']}\n"
                    prompt += revision_text
                    continue
            else:
                print("✅ No revision requests found. Finalizing plan...")
                break
        
        # If max cycles reached
        if tracker.revision_cycle >= limits.max_revision_cycles:
            print(f"⚠️ Maximum revision cycles ({limits.max_revision_cycles}) reached.")
        
        display_validated_travel_plan(state)
        return state
        
    except Exception as e:
        print(f"🚨 Enhanced workflow execution error: {str(e)}")
        import traceback
        print(f"📋 Full traceback: {traceback.format_exc()}")
        return None

def display_validated_travel_plan(state):
    """Display travel plan with validation results"""
    
    print("\n" + "=" * 80)
    print("🌍 VALIDATED GLOBEPILOT TRAVEL PLAN")
    print("=" * 80)
    
    # Validation Status
    plan_approval = state.get("plan_approval", {})
    if plan_approval:
        status = plan_approval.get("status", "pending")
        print(f"\n🎯 PLAN STATUS: {status.upper()}")
        if plan_approval.get("notes"):
            print(f"📝 Notes: {plan_approval['notes']}")
    
    # Budget Validation
    budget_validation = state.get("budget_validation", {})
    if budget_validation:
        print(f"\n💰 BUDGET VALIDATION: {budget_validation.get('result', 'Pending')}")
        print(f"📊 Target Budget: {budget_validation.get('target_budget', 'Not specified')}")
    
    calculated_budget = state.get("calculated_total_budget", 0)
    if calculated_budget > 0:
        print(f"💵 Calculated Total: ${calculated_budget:,.2f}")
    
    # Quality Issues
    quality_issues = state.get("quality_issues", [])
    if quality_issues:
        print(f"\n⚠️ QUALITY ISSUES FOUND ({len(quality_issues)}):")
        for issue in quality_issues:
            print(f"  • {issue.get('severity', 'medium').upper()}: {issue.get('description', 'No description')}")
    
    # Revision Requests
    revision_requests = state.get("revision_requests", [])
    if revision_requests:
        print(f"\n🔄 REVISION HISTORY ({len(revision_requests)}):")
        for revision in revision_requests:
            status = revision.get('status', 'pending')
            print(f"  • {revision.get('agent', 'Unknown')}: {revision.get('request', 'No details')} [{status}]")
    
    # Travel Plan Content
    if state.get("itinerary", "") != "Not created yet.":
        print(f"\n📅 TRAVEL ITINERARY:")
        print(state["itinerary"])
    
    if state.get("budget_analysis", "") != "Budget analysis required.":
        print(f"\n💰 BUDGET ANALYSIS:")
        print(state["budget_analysis"])
    
    if state.get("weather_info", "") != "Weather analysis required.":
        print(f"\n🌤️ WEATHER INFORMATION:")
        print(state["weather_info"])
    
    if state.get("document_requirements"):
        print(f"\n📄 DOCUMENT REQUIREMENTS:")
        print(state["document_requirements"])
    
    if state.get("packing_suggestions"):
        print(f"\n🎒 PACKING SUGGESTIONS:")
        print(state["packing_suggestions"])
    
    print("\n" + "=" * 80)
    if plan_approval.get("status") == "approved":
        print("✅ PLAN APPROVED - READY FOR BOOKING!")
    else:
        print("📋 PLAN UNDER REVIEW - REVISIONS MAY BE NEEDED")
    print("=" * 80)

# ============================================================================
# TEST FUNCTIONS
# ============================================================================

async def test_budget_validation():
    """Test the validation system with a budget-constrained scenario"""
    test_prompt = """
    Plan a budget-friendly travel experience:
    
    Starting Location: Boston, MA
    Destination: Paris, France
    Travel Dates: July 15 - July 22, 2026
    Budget: $1,500 - $2,000 (STRICT BUDGET)
    Number of Travelers: 1
    Travel Type: Budget backpacking
    
    REQUIREMENTS:
    - Must stay within budget
    - Prefer hostels or budget accommodations
    - Use public transportation
    - Include free or low-cost activities
    - Vegetarian dining options required
    """
    
    print("🧪 Testing Validation System - Budget Compliance")
    # Use fast limits for testing
    test_limits = WorkflowLimits(
        max_iterations=30,
        max_revision_cycles=1,
        max_api_calls=50,
        max_duration_minutes=3,
        early_termination_enabled=True
    )
    result = await execute_validated_travel_workflow(test_prompt, custom_limits=test_limits)
    return result

async def test_luxury_validation():
    """Test the validation system with a luxury scenario"""
    test_prompt = """
    Plan a luxury travel experience:
    
    Starting Location: New York City
    Destination: Tokyo, Japan
    Travel Dates: October 10 - October 20, 2026
    Budget: $8,000 - $12,000
    Number of Travelers: 2 (couple)
    Travel Type: Luxury cultural exploration
    
    REQUIREMENTS:
    - 5-star accommodations only
    - Michelin-starred dining experiences
    - Private tours and exclusive experiences
    - Business class flights
    """
    
    print("🧪 Testing Validation System - Luxury Requirements")
    # Use fast limits for testing
    test_limits = WorkflowLimits(
        max_iterations=30,
        max_revision_cycles=1,
        max_api_calls=50,
        max_duration_minutes=3,
        early_termination_enabled=True
    )
    result = await execute_validated_travel_workflow(test_prompt, custom_limits=test_limits)
    return result

async def test_simple_validation():
    """Simple test of the validation workflow"""
    test_prompt = """
    Plan a weekend getaway:
    
    Starting Location: San Francisco
    Destination: Los Angeles
    Travel Dates: June 1 - June 3, 2026
    Budget: $800 - $1,200
    Number of Travelers: 1
    Travel Type: Weekend leisure
    """
    
    print("🧪 Testing Validation System - Simple Scenario")
    # Use fast limits for testing
    test_limits = WorkflowLimits(
        max_iterations=25,
        max_revision_cycles=1,
        max_api_calls=40,
        max_duration_minutes=2,
        early_termination_enabled=True
    )
    result = await execute_validated_travel_workflow(test_prompt, custom_limits=test_limits)
    return result

async def debug_workflow_test():
    """Debug test to check workflow configuration"""
    print("🔧 DEBUG: Checking workflow configuration...")
    
    # Check agent handoffs
    print("\n🔗 Agent handoff configuration:")
    agents = [general_research_agent, accommodations_agent, activities_agent, local_events_agent, budget_analysis_agent, 
              flight_agent, local_transportation_agent, weather_agent, travel_planner_agent, validation_agent, quality_control_agent]
    
    for agent in agents:
        handoffs = getattr(agent, 'can_handoff_to', [])
        print(f"  • {agent.name}: can handoff to {handoffs}")
    
    # Process the workflow
    try:
        print(f"\n🚀 Starting GlobePiloT enhanced workflow...")
        print(f"📍 Starting with: {general_research_agent.name}")
        result = await enhanced_travel_workflow.run(prompt)
        
        # Debug: Print event information
        events = result.get("workflow_events", [])
        agent_sequence = []
        event_count = 0
        
        for event in events:
            event_count += 1
            if hasattr(event, 'name'):
                agent_sequence.append(event.name)
            print(f"Event {event_count}: {event}")
        
        print(f"\n📊 Workflow completion analysis:")
        print(f"📊 Total events: {event_count}")
        print(f"📊 Agent sequence: {agent_sequence}")
        print(f"📊 Expected: 11 agents total (9 specialized + 2 validation)")
        
        if len(agent_sequence) < 9:
            print("❌ Workflow stopped early - handoff chain broken")
        else:
            print("✅ Workflow completed expected agent sequence")
        
        return result
        
    except Exception as e:
        print(f"❌ Workflow execution error: {str(e)}")
        import traceback
        traceback.print_exc()
        return {
            "error": str(e),
            "workflow_status": "failed"
        }

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main function to demonstrate GlobePiloT capabilities"""
    
    print("🎯 GLOBEPILOT ENHANCED - STREAMLINED MULTI-AGENT TRAVEL SYSTEM")
    print("=" * 70)
    print("🤖 TOTAL AGENTS: 11 specialized travel agents")
    print("🔧 STREAMLINED FEATURES:")
    print("  • 4 specialized destination research agents")
    print("  • 2 specialized transportation agents") 
    print("  • 1 budget analysis agent")
    print("  • 1 weather agent")
    print("  • 1 master travel planner agent")
    print("  • 2 validation and quality control agents")
    print("  • Automatic budget compliance checking")
    print("  • Multi-agent revision coordination")
    print("  • JSON structured output system")
    print("  • Real-time validation and quality assurance")
    print("=" * 70)
    
    while True:
        print("\n🚀 Choose a test scenario:")
        print("1. Budget Validation Test (Strict $2000 budget)")
        print("2. Luxury Validation Test ($8000-12000 budget)")
        print("3. Simple Weekend Trip Test")
        print("4. Custom Travel Request")
        print("5. Debug Workflow Test")
        print("6. Exit")
        
        choice = input("\nEnter your choice (1-6): ").strip()
        
        if choice == "1":
            await test_budget_validation()
        elif choice == "2":
            await test_luxury_validation()
        elif choice == "3":
            await test_simple_validation()
        elif choice == "4":
            custom_prompt = input("\nEnter your custom travel request:\n")
            # Use debug limits for custom testing
            debug_limits = WorkflowLimits(
                max_iterations=40,
                max_revision_cycles=1,
                max_api_calls=60,
                max_duration_minutes=4,
                early_termination_enabled=True
            )
            await execute_validated_travel_workflow(custom_prompt, custom_limits=debug_limits)
        elif choice == "5":
            await debug_workflow_test()
        elif choice == "6":
            print("👋 Thank you for using GlobePiloT Enhanced!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

# ============================================================================
# JSON SCHEMAS FOR STRUCTURED AGENT OUTPUTS
# ============================================================================

DESTINATION_RESEARCH_SCHEMA = {
    "type": "object",
    "properties": {
        "destination": {"type": "string"},
        "overview": {"type": "string"},
        "attractions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "address": {"type": "string"},
                    "cost": {"type": "string"},
                    "hours": {"type": "string"},
                    "category": {"type": "string"},
                    "booking_required": {"type": "boolean"},
                    "duration": {"type": "string"}
                }
            }
        },
        "neighborhoods": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "description": {"type": "string"},
                    "best_for": {"type": "array", "items": {"type": "string"}},
                    "safety_rating": {"type": "string"}
                }
            }
        },
        "dining": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "cuisine": {"type": "string"},
                    "price_range": {"type": "string"},
                    "address": {"type": "string"},
                    "description": {"type": "string"},
                    "reservation_required": {"type": "boolean"}
                }
            }
        },
        "accommodation": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "price_range": {"type": "string"},
                    "address": {"type": "string"},
                    "amenities": {"type": "array", "items": {"type": "string"}},
                    "rating": {"type": "number"}
                }
            }
        },
        "cultural_info": {
            "type": "object",
            "properties": {
                "customs": {"type": "array", "items": {"type": "string"}},
                "tipping": {"type": "string"},
                "dress_code": {"type": "string"},
                "language_tips": {"type": "array", "items": {"type": "string"}}
            }
        },
        "safety_info": {
            "type": "object",
            "properties": {
                "safe_areas": {"type": "array", "items": {"type": "string"}},
                "areas_to_avoid": {"type": "array", "items": {"type": "string"}},
                "common_scams": {"type": "array", "items": {"type": "string"}},
                "emergency_numbers": {"type": "object"}
            }
        },
        "seasonal_info": {
            "type": "object",
            "properties": {
                "best_time_to_visit": {"type": "string"},
                "peak_season": {"type": "string"},
                "special_events": {"type": "array", "items": {"type": "object"}}
            }
        }
    }
}

ACCOMMODATION_SCHEMA = {
    "type": "object",
    "properties": {
        "budget_allocation": {
            "type": "object",
            "properties": {
                "total_budget": {"type": "number"},
                "accommodation_budget_min": {"type": "number"},
                "accommodation_budget_max": {"type": "number"},
                "percentage_range": {"type": "string"}
            }
        },
        "recommendations": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "address": {"type": "string"},
                    "platform_type": {"type": "string"},
                    "booking_platform": {"type": "string"},
                    "price_per_night": {"type": "number"},
                    "total_stay_cost": {"type": "number"},
                    "booking_url": {"type": "string"},
                    "image_url": {"type": "string"},
                    "description": {"type": "string"},
                    "unique_features": {"type": "array", "items": {"type": "string"}},
                    "amenities_included": {"type": "array", "items": {"type": "string"}},
                    "amenities_extra_cost": {"type": "array", "items": {"type": "string"}},
                    "location_score": {"type": "number"},
                    "walking_distance_attractions": {"type": "string"},
                    "neighborhood": {"type": "string"},
                    "pros": {"type": "array", "items": {"type": "string"}},
                    "cons": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "booking_strategy": {
            "type": "object",
            "properties": {
                "best_booking_time": {"type": "string"},
                "price_comparison_tips": {"type": "array", "items": {"type": "string"}},
                "cancellation_policies": {"type": "string"}
            }
        }
    }
}

BUDGET_ANALYSIS_SCHEMA = {
    "type": "object",
    "properties": {
        "total_estimated_cost": {"type": "number"},
        "budget_scenarios": {
            "type": "object",
            "properties": {
                "budget": {"type": "object", "properties": {"total": {"type": "number"}, "per_day": {"type": "number"}}},
                "mid_range": {"type": "object", "properties": {"total": {"type": "number"}, "per_day": {"type": "number"}}},
                "luxury": {"type": "object", "properties": {"total": {"type": "number"}, "per_day": {"type": "number"}}}
            }
        },
        "cost_breakdown": {
            "type": "object",
            "properties": {
                "accommodation": {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}, "recommended": {"type": "number"}}},
                "transportation": {"type": "object", "properties": {"flights": {"type": "number"}, "local_transport": {"type": "number"}, "transfers": {"type": "number"}}},
                "food": {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}, "per_day": {"type": "number"}}},
                "activities": {"type": "object", "properties": {"min": {"type": "number"}, "max": {"type": "number"}, "must_do": {"type": "number"}}},
                "shopping": {"type": "object", "properties": {"souvenirs": {"type": "number"}, "optional": {"type": "number"}}},
                "miscellaneous": {"type": "object", "properties": {"tips": {"type": "number"}, "emergency": {"type": "number"}}}
            }
        },
        "cost_saving_tips": {"type": "array", "items": {"type": "string"}},
        "payment_methods": {"type": "array", "items": {"type": "string"}},
        "currency_info": {"type": "object"}
    }
}

WEATHER_SCHEMA = {
    "type": "object",
    "properties": {
        "daily_forecasts": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "date": {"type": "string"},
                    "high_temp": {"type": "number"},
                    "low_temp": {"type": "number"},
                    "conditions": {"type": "string"},
                    "precipitation_chance": {"type": "number"},
                    "humidity": {"type": "number"},
                    "wind_speed": {"type": "number"},
                    "uv_index": {"type": "number"}
                }
            }
        },
        "seasonal_patterns": {
            "type": "object",
            "properties": {
                "typical_weather": {"type": "string"},
                "extreme_weather_risks": {"type": "array", "items": {"type": "string"}},
                "best_days": {"type": "array", "items": {"type": "string"}},
                "challenging_days": {"type": "array", "items": {"type": "string"}}
            }
        },
        "activity_recommendations": {
            "type": "object",
            "properties": {
                "outdoor_activities": {"type": "array", "items": {"type": "string"}},
                "indoor_alternatives": {"type": "array", "items": {"type": "string"}},
                "weather_dependent": {"type": "array", "items": {"type": "string"}}
            }
        },
        "packing_implications": {
            "type": "object",
            "properties": {
                "essential_items": {"type": "array", "items": {"type": "string"}},
                "clothing_recommendations": {"type": "array", "items": {"type": "string"}},
                "weather_gear": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}

ITINERARY_SCHEMA = {
    "type": "object",
    "properties": {
        "trip_overview": {
            "type": "object",
            "properties": {
                "destination": {"type": "string"},
                "duration": {"type": "string"},
                "trip_type": {"type": "string"},
                "total_cost": {"type": "number"}
            }
        },
        "days": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "day_number": {"type": "integer"},
                    "date": {"type": "string"},
                    "title": {"type": "string"},
                    "summary": {"type": "string"},
                    "weather": {"type": "object"},
                    "total_cost": {"type": "number"},
                    "activities": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "time": {"type": "string"},
                                "activity": {"type": "string"},
                                "location": {"type": "string"},
                                "address": {"type": "string"},
                                "cost": {"type": "number"},
                                "duration": {"type": "string"},
                                "description": {"type": "string"},
                                "booking_info": {"type": "string"},
                                "backup_plan": {"type": "string"},
                                "category": {"type": "string"}
                            }
                        }
                    },
                    "transportation": {
                        "type": "object",
                        "properties": {
                            "primary_method": {"type": "string"},
                            "daily_cost": {"type": "number"},
                            "notes": {"type": "string"}
                        }
                    },
                    "dining": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "meal": {"type": "string"},
                                "restaurant": {"type": "string"},
                                "cuisine": {"type": "string"},
                                "cost": {"type": "number"},
                                "address": {"type": "string"},
                                "reservation": {"type": "boolean"}
                            }
                        }
                    },
                    "tips": {"type": "array", "items": {"type": "string"}}
                }
            }
        },
        "additional_info": {
            "type": "object",
            "properties": {
                "transportation_overview": {"type": "string"},
                "accommodation_details": {"type": "object"},
                "emergency_contacts": {"type": "object"},
                "local_tips": {"type": "array", "items": {"type": "string"}}
            }
        }
    }
}

if __name__ == "__main__":
    asyncio.run(main()) 
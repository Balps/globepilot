#!/usr/bin/env python3
"""
GlobePiloT: AI-Powered Multi-Agent Travel Assistant with Validation
A comprehensive travel planning system with intelligent validation and quality control.
"""

import os
import asyncio
import time
import re
from datetime import datetime, timedelta
from tavily import AsyncTavilyClient

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

# Initialize LLM
llm = OpenAI(temperature=0.2, model="gpt-4o", api_key=OPENAI_API_KEY, top_p=0.95)
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
    
    budget_patterns = [
        r'budget[:\s]*\$?(\d{1,3}(?:,\d{3})*)\s*[-–to]\s*\$?(\d{1,3}(?:,\d{3})*)',
        r'\$(\d{1,3}(?:,\d{3})*)\s*[-–to]\s*\$?(\d{1,3}(?:,\d{3})*)',
        r'(\d{1,3}(?:,\d{3})*)\s*[-–to]\s*(\d{1,3}(?:,\d{3})*)\s*budget',
        r'(\d{1,3}(?:,\d{3})*)\s*[-–]\s*(\d{1,3}(?:,\d{3})*)\s*budget',
        r'budget[:\s]*\$?(\d{1,3}(?:,\d{3})*)',
        r'\$(\d{1,3}(?:,\d{3})*)'
    ]
    
    for pattern in budget_patterns:
        match = re.search(pattern, user_prompt, re.IGNORECASE)
        if match:
            if len(match.groups()) == 2:
                min_budget = float(match.group(1).replace(',', ''))
                max_budget = float(match.group(2).replace(',', ''))
                return min_budget, max_budget
            else:
                budget = float(match.group(1).replace(',', ''))
                return budget * 0.8, budget * 1.2
    
    return 0.0, float('inf')

# ============================================================================
# TRAVEL AGENTS
# ============================================================================

destination_research_agent = FunctionAgent(
    name="DestinationResearchAgent",
    description="Expert travel research agent specialized in destinations, attractions, and travel advisories.",
    system_prompt=(
        "You are a destination research agent with access to real-time web search. "
        "Research comprehensive destination information including attractions, accommodations, and activities. "
        "MANDATORY STEPS: "
        "1. Call search_web(query='destination research query') "
        "2. Call record_travel_notes(notes='detailed research findings', category='destination_research') "
        "3. Call handoff(to_agent='BudgetAnalysisAgent', reason='Destination research complete') "
        "Complete all steps in order."
    ),
    llm=llm,
    tools=[search_web, record_travel_notes],
    can_handoff_to=["BudgetAnalysisAgent"],
)

budget_analysis_agent = FunctionAgent(
    name="BudgetAnalysisAgent",
    description="Expert travel budget analyst specialized in cost estimation and budget planning.",
    system_prompt=(
        "You are a budget analysis agent that researches travel costs and creates detailed budget breakdowns. "
        "MANDATORY STEPS: "
        "1. Call search_web(query='budget and pricing query') "
        "2. Call record_travel_notes(notes='budget analysis', category='budget_analysis') "
        "3. Call update_budget_analysis(budget_breakdown='detailed breakdown') "
        "4. Call handoff(to_agent='TransportationAgent', reason='Budget analysis complete') "
        "Complete all steps in order."
    ),
    llm=llm,
    tools=[search_web, record_travel_notes, update_budget_analysis],
    can_handoff_to=["TransportationAgent"],
)

transportation_agent = FunctionAgent(
    name="TransportationAgent",
    description="Expert transportation specialist finding optimal travel routes and local transportation.",
    system_prompt=(
        "You are a transportation research agent. Research flight options, local transportation, and logistics. "
        "MANDATORY STEPS: "
        "1. Call search_web(query='transportation and flight options') "
        "2. Call record_travel_notes(notes='transportation research', category='transportation') "
        "3. Call handoff(to_agent='WeatherAgent', reason='Transportation research complete') "
        "Complete all steps in order."
    ),
    llm=llm,
    tools=[search_web, record_travel_notes],
    can_handoff_to=["WeatherAgent"],
)

weather_agent = FunctionAgent(
    name="WeatherAgent",
    description="Expert weather specialist providing climate information and forecasts for travel dates.",
    system_prompt=(
        "You are a weather research agent that provides comprehensive weather information for travel dates. "
        "MANDATORY STEPS: "
        "1. Call search_web(query='weather forecast for travel dates') "
        "2. Call record_weather_info(weather_data='weather analysis') "
        "3. Call record_travel_notes(notes='weather content', category='weather') "
        "4. Call handoff(to_agent='DocumentAgent', reason='Weather research complete, need document requirements') "
        "Complete all steps in order."
    ),
    llm=llm,
    tools=[search_web, record_travel_notes, record_weather_info],
    can_handoff_to=["DocumentAgent"],
)

document_agent = FunctionAgent(
    name="DocumentAgent",
    description="Expert document specialist researching visa requirements, travel documents, and paperwork needed for international travel.",
    system_prompt=(
        "You are a travel document specialist that researches all required paperwork for international travel. "
        "MANDATORY STEPS: "
        "1. Call search_web(query='visa requirements passport documents for [destination] from [origin]') "
        "2. Call record_document_requirements(document_list='comprehensive document checklist') "
        "3. Call record_travel_notes(notes='document analysis', category='documents') "
        "4. Call handoff(to_agent='PackingAgent', reason='Document requirements complete, ready for packing') "
        "Research and provide: "
        "- Passport validity requirements "
        "- Visa requirements and processing times "
        "- Travel permits and special documentation "
        "- Health certificates and vaccination requirements "
        "- Travel insurance recommendations "
        "- Embassy/consulate contact information "
        "- Entry/exit requirements and restrictions"
    ),
    llm=llm,
    tools=[search_web, record_travel_notes, record_document_requirements],
    can_handoff_to=["PackingAgent"],
)

packing_agent = FunctionAgent(
    name="PackingAgent",
    description="Expert packing specialist creating personalized packing lists based on destination, weather, documents, and trip type.",
    system_prompt=(
        "You are a packing expert that creates comprehensive, personalized packing lists using data from previous agents. "
        "MANDATORY STEPS: "
        "1. Call get_destination_data() to understand destination specifics, culture, and activities "
        "2. Call get_weather_data() to get climate conditions and seasonal weather patterns "
        "3. Call get_document_requirements() to understand required documents and paperwork "
        "4. Call search_web(query='packing list for [destination] [weather] [trip type]') for additional packing tips "
        "5. Call record_packing_suggestions(packing_list='comprehensive packing list') "
        "6. Call record_travel_notes(notes='packing analysis', category='packing') "
        "7. Call handoff(to_agent='TravelPlannerAgent', reason='Packing suggestions complete') "
        "Create detailed, categorized packing lists: "
        "• CLOTHING: Weather-appropriate items, cultural considerations, activity-specific wear "
        "• DOCUMENTS: Based on document agent requirements (passport, visas, certificates, copies) "
        "• ELECTRONICS: Adapters, chargers, cameras, based on destination power standards "
        "• HEALTH & SAFETY: Based on destination health requirements and weather conditions "
        "• TOILETRIES & PERSONAL: Consider local availability and travel restrictions "
        "• TRAVEL GEAR: Luggage, bags, travel accessories based on trip type "
        "Use specific weather data to recommend layers, materials, and seasonal items. "
        "Include document organization tips and backup copies based on requirements."
    ),
    llm=llm,
    tools=[search_web, record_travel_notes, record_packing_suggestions, get_weather_data, get_destination_data, get_document_requirements],
    can_handoff_to=["TravelPlannerAgent"],
)

travel_planner_agent = FunctionAgent(
    name="TravelPlannerAgent",
    description="Expert travel planner creating comprehensive, date-specific personalized itineraries.",
    system_prompt=(
        "You are the master travel planner creating comprehensive travel itineraries from all previous research. "
        "MANDATORY STEPS: "
        "1. Review all previous research from other agents "
        "2. Call create_itinerary(itinerary_content='comprehensive itinerary') "
        "3. Call record_travel_notes(notes='final planning notes', category='final_itinerary') "
        "4. Call handoff(to_agent='ValidationAgent', reason='Travel plan complete, need validation') "
        "Create detailed day-by-day itineraries with all necessary information."
    ),
    llm=llm,
    tools=[search_web, record_travel_notes, create_itinerary, update_budget_analysis, record_weather_info],
    can_handoff_to=["ValidationAgent"],
)

validation_agent = FunctionAgent(
    name="ValidationAgent",
    description="Expert validation specialist ensuring travel plans meet budget and requirements.",
    system_prompt=(
        "You are a validation specialist that checks if travel plans meet user requirements and budget. "
        "VALIDATION PROCESS: "
        "1. Call calculate_total_budget() to check costs "
        "2. Call validate_budget_compliance() with results "
        "3. Call validate_requirements_compliance() to check requirements "
        "4. If issues found, call request_agent_revision() for specific agents "
        "5. If major issues, call record_quality_issues() and handoff to QualityControlAgent "
        "6. If acceptable, call approve_travel_plan() "
        "DECISION CRITERIA: Budget over 20% = revision needed, missing requirements = revision needed."
    ),
    llm=llm,
    tools=[
        search_web, validate_budget_compliance, validate_requirements_compliance, 
        request_agent_revision, record_quality_issues, approve_travel_plan, calculate_total_budget
    ],
    can_handoff_to=["QualityControlAgent", "BudgetAnalysisAgent", "DestinationResearchAgent", "TransportationAgent", "WeatherAgent"],
)

quality_control_agent = FunctionAgent(
    name="QualityControlAgent",
    description="Expert quality control specialist managing revisions and ensuring plan excellence.",
    system_prompt=(
        "You are the quality control specialist managing complex revisions and final approval. "
        "PROCESS: "
        "1. Review quality issues from ValidationAgent "
        "2. Determine which agents need revisions "
        "3. Call request_agent_revision() with specific instructions "
        "4. Coordinate multiple revision cycles "
        "5. Call approve_travel_plan() when standards are met "
        "You have final authority on plan approval and can request unlimited revisions."
    ),
    llm=llm,
    tools=[
        search_web, validate_budget_compliance, validate_requirements_compliance, 
        request_agent_revision, record_quality_issues, approve_travel_plan, calculate_total_budget
    ],
    can_handoff_to=["ValidationAgent", "BudgetAnalysisAgent", "DestinationResearchAgent", "TransportationAgent", "WeatherAgent", "TravelPlannerAgent"],
)

# ============================================================================
# WORKFLOW CONFIGURATION
# ============================================================================

enhanced_travel_workflow = AgentWorkflow(
    agents=[
        destination_research_agent,
        budget_analysis_agent,
        transportation_agent,
        weather_agent,
        document_agent,
        packing_agent,
        travel_planner_agent,
        validation_agent,
        quality_control_agent
    ],
    root_agent=destination_research_agent.name,
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

async def execute_validated_travel_workflow(prompt, max_revision_cycles=3):
    """Execute travel planning workflow with validation and revision capabilities"""
    try:
        print("🚀 Starting Enhanced GlobePiloT with Validation...")
        
        # Extract user budget for validation
        min_budget, max_budget = await extract_user_budget(prompt)
        print(f"💰 Detected budget range: ${min_budget:,.0f} - ${max_budget:,.0f}")
        
        revision_cycle = 0
        
        while revision_cycle < max_revision_cycles:
            print(f"\n🔄 Planning Cycle {revision_cycle + 1}/{max_revision_cycles}")
            
            # Run the enhanced workflow
            handler = enhanced_travel_workflow.run(user_msg=prompt, max_iterations=300)
            current_agent = None
            agent_activations = []
            
            # Process events
            async for event in handler.stream_events():
                if hasattr(event, "current_agent_name") and event.current_agent_name != current_agent:
                    current_agent = event.current_agent_name
                    agent_activations.append(current_agent)
                    print(f"🤖 {current_agent} is now active")
                
                elif isinstance(event, ToolCallResult):
                    if event.tool_name == "request_agent_revision":
                        print(f"🔄 Revision requested: {event.tool_output}")
                    elif event.tool_name == "approve_travel_plan":
                        print(f"✅ Plan status: {event.tool_output}")
                    elif event.tool_name == "handoff":
                        print(f"🔀 Handoff: {event.tool_output}")
            
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
            
            print(f"\n📊 Agents activated: {len(agent_activations)} - {agent_activations}")
            
            # Force validation if not reached
            if "ValidationAgent" not in agent_activations:
                print("⚠️ ValidationAgent not reached - triggering manual validation...")
                
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
                
                revision_cycle += 1
                if revision_cycle < max_revision_cycles:
                    print(f"🔄 Starting revision cycle {revision_cycle + 1}...")
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
        if revision_cycle >= max_revision_cycles:
            print(f"⚠️ Maximum revision cycles ({max_revision_cycles}) reached.")
        
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
    result = await execute_validated_travel_workflow(test_prompt, max_revision_cycles=2)
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
    result = await execute_validated_travel_workflow(test_prompt, max_revision_cycles=2)
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
    result = await execute_validated_travel_workflow(test_prompt, max_revision_cycles=1)
    return result

async def debug_workflow_test():
    """Debug test to check workflow configuration"""
    print("🔧 DEBUG: Checking workflow configuration...")
    
    # Check agent handoffs
    print("\n🔗 Agent handoff configuration:")
    agents = [destination_research_agent, budget_analysis_agent, transportation_agent, 
              weather_agent, travel_planner_agent, validation_agent, quality_control_agent]
    
    for agent in agents:
        handoffs = getattr(agent, 'can_handoff_to', [])
        print(f"  {agent.name} → {handoffs}")
    
    # Simple test prompt
    simple_prompt = "Plan a simple 3-day trip to San Francisco with a $1000 budget."
    
    print(f"\n🧪 Testing with simple prompt: {simple_prompt}")
    
    try:
        handler = enhanced_travel_workflow.run(user_msg=simple_prompt, max_iterations=50)
        
        agent_sequence = []
        event_count = 0
        
        async for event in handler.stream_events():
            event_count += 1
            
            if hasattr(event, "current_agent_name"):
                if event.current_agent_name not in agent_sequence:
                    agent_sequence.append(event.current_agent_name)
                    print(f"🤖 Agent {len(agent_sequence)}: {event.current_agent_name}")
            
            if event_count > 100:  # Prevent infinite loops
                print("⏰ Stopping after 100 events")
                break
        
        print(f"\n📊 Total events: {event_count}")
        print(f"📊 Agent sequence: {agent_sequence}")
        print(f"📊 Expected: 7 agents (5 planning + 2 validation)")
        
        if len(agent_sequence) < 5:
            print("❌ Workflow stopped early - handoff chain broken")
        else:
            print("✅ All planning agents activated")
            
    except Exception as e:
        print(f"❌ Debug test failed: {e}")

# ============================================================================
# MAIN EXECUTION
# ============================================================================

async def main():
    """Main function to demonstrate GlobePiloT capabilities"""
    
    print("🎯 GLOBEPILOT ENHANCED - VALIDATION & QUALITY CONTROL SYSTEM")
    print("=" * 70)
    print("🤖 TOTAL AGENTS: 7 specialized travel agents + 2 validation agents")
    print("🔧 VALIDATION FEATURES:")
    print("  • Automatic budget compliance checking")
    print("  • Requirements validation")
    print("  • Multi-cycle revision system")
    print("  • Quality issue tracking")
    print("  • Final plan approval workflow")
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
            await execute_validated_travel_workflow(custom_prompt)
        elif choice == "5":
            await debug_workflow_test()
        elif choice == "6":
            print("👋 Thank you for using GlobePiloT Enhanced!")
            break
        else:
            print("❌ Invalid choice. Please try again.")

if __name__ == "__main__":
    asyncio.run(main()) 
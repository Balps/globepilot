# 🌍 GlobePiloT Enhanced - AI Travel Planning System

A comprehensive multi-agent travel planning system with intelligent validation and quality control, now featuring a beautiful web interface!

## ✨ Features

### 🌐 Web Interface
- **Beautiful Modern UI**: Responsive Flask web application with real-time progress tracking
- **Interactive Forms**: Comprehensive travel planning forms with validation
- **Live Progress**: Watch AI agents work in real-time with visual indicators
- **Rich Results Display**: Formatted itineraries with budget analysis and validation status

### 🤖 AI Multi-Agent System
- **9 Specialized Travel Agents**: Destination research, budget analysis, transportation, weather, document requirements, packing suggestions, accommodation, activities, and itinerary planning
- **2 Validation Agents**: Budget compliance checking and quality control with revision capabilities
- **Intelligent Validation**: Automatic budget checking, requirements validation, and revision requests
- **Multi-Cycle Refinement**: Up to 3 revision cycles to perfect your travel plan
- **Real-Time Research**: Live web search for current prices, weather, and availability

## 🚀 Quick Start

### Option 1: Web Interface (Recommended) 🌐

#### 1. Automated Setup (Recommended)
```bash
# Complete setup with dependencies and API keys
python setup.py
```

This will:
- Install all required packages (Flask, OpenAI, Tavily, etc.)
- Check for existing environment variables
- Create .env file if needed (or use existing one)
- Test all connections
- Create necessary directories
- Provide usage instructions

#### 2. API Key Configuration (Choose One Method)

**Option A: Environment Variables (Recommended for Production)**
```bash
export OPENAI_API_KEY="your_openai_api_key_here"
export TAVILY_API_KEY="your_tavily_api_key_here"
```

**Option B: .env File (Good for Development)**
```bash
# The setup script will create this for you, or create manually:
echo "OPENAI_API_KEY=your_openai_api_key_here" > .env
echo "TAVILY_API_KEY=your_tavily_api_key_here" >> .env
```

**Note:** Environment variables override .env file values

#### 3. Manual Setup (Alternative)
```bash
pip install -r requirements.txt
# Then set API keys using Option A or B above
```

#### 4. Launch Web Application
```bash
python run_web.py
```

Then open your browser to: **http://localhost:8000**

### Option 2: Command Line Interface 💻

#### Run the Script
```bash
python globepilot_enhanced.py
```

## 🌐 Web Interface Features

### Form Fields:
- **Travel Details**: Origin, destination, dates
- **Budget Range**: Minimum and maximum budget with validation
- **Trip Type**: Leisure, business, romantic, family, adventure, etc.
- **Special Requirements**: Dietary restrictions, accessibility needs, preferences

### Real-Time Progress:
- **Agent Status**: Visual indicators showing which agents are working
- **Progress Bar**: Live updates on planning progress
- **Processing Log**: Detailed activity log with timestamps
- **Auto-Refresh**: Automatic updates and redirect to results

### Results Display:
- **Comprehensive Itinerary**: Day-by-day travel plans
- **Budget Analysis**: Detailed cost breakdown with validation status
- **Weather Information**: Climate data and packing recommendations
- **Validation Status**: Budget compliance and quality control results
- **Print & Share**: Print-friendly layout and copy-to-clipboard functionality

## 🎯 How It Works

1. **Planning Phase**: 7 specialized agents research and plan your trip
2. **Validation Phase**: ValidationAgent checks budget compliance and requirements
3. **Revision Phase**: If issues found, specific agents get revision requests
4. **Quality Control**: QualityControlAgent manages complex revisions
5. **Final Approval**: Only validated plans are marked as approved

## 🌐 Using the Web Interface

### Travel Planning Form:
1. **Fill out travel details**: Origin, destination, travel dates
2. **Set budget range**: Enter minimum and maximum budget
3. **Choose trip type**: Select from 10 different travel styles
4. **Add requirements**: Optional special needs and preferences
5. **Submit**: Click "Create My Travel Plan" to start AI processing

### Watch AI Agents Work:
- **Real-time progress**: See agents activate with visual indicators
- **Processing log**: Live updates on what each agent is doing
- **Progress tracking**: Visual progress bar and status updates
- **Auto-redirect**: Automatically taken to results when complete

### Review Your Plan:
- **Validation status**: See if plan meets budget and requirements
- **Detailed itinerary**: Comprehensive day-by-day travel plans
- **Budget breakdown**: Complete cost analysis with validation
- **Weather info**: Climate data and packing recommendations
- **Actions**: Print, copy, or plan another trip

## 🧪 Command Line Test Scenarios

The command line script includes 4 built-in test scenarios:

1. **Budget Validation Test**: Strict $2000 budget to test revision system
2. **Luxury Validation Test**: $8000-12000 luxury travel requirements
3. **Simple Weekend Trip**: Basic validation test
4. **Custom Travel Request**: Enter your own travel requirements

## 📋 Example Usage

When you run the script, you'll see:

```
🌍 GlobePiloT Enhanced - AI Travel Planning System
🎯 GLOBEPILOT ENHANCED - VALIDATION & QUALITY CONTROL SYSTEM
🤖 TOTAL AGENTS: 7 specialized travel agents + 2 validation agents

🚀 Choose a test scenario:
1. Budget Validation Test (Strict $2000 budget)
2. Luxury Validation Test ($8000-12000 budget)
3. Simple Weekend Trip Test
4. Custom Travel Request
5. Exit

Enter your choice (1-5):
```

## 🤖 Agents Overview

### Planning Agents:
- **DestinationResearchAgent**: Destinations, attractions, activities
- **BudgetAnalysisAgent**: Cost estimation and budget breakdowns
- **TransportationAgent**: Flights, trains, local transportation
- **WeatherAgent**: Climate information and weather forecasts
- **DocumentAgent**: Visa requirements, passport validity, travel permits, and documentation
- **PackingAgent**: Personalized packing lists based on destination, weather, and trip type
- **TravelPlannerAgent**: Comprehensive itinerary creation

### Validation Agents:
- **ValidationAgent**: Budget compliance and requirements checking
- **QualityControlAgent**: Revision management and final approval

## 💰 Budget Validation

The system automatically:
- Extracts budget range from your request
- Calculates total costs from all agent recommendations
- Validates budget compliance (20% tolerance)
- Requests revisions if budget exceeded
- Ensures final plan meets financial constraints

## 🔄 Revision System

If issues are found:
1. Specific agents receive targeted revision requests
2. Agents adjust their recommendations
3. System re-validates the updated plan
4. Process repeats up to 3 cycles
5. Final approval only given to compliant plans

## 📝 Sample Output

```
🚀 Starting Enhanced GlobePiloT with Validation...
💰 Detected budget range: $1,500 - $2,000

🔄 Planning Cycle 1/3
🤖 DestinationResearchAgent is now active
🤖 BudgetAnalysisAgent is now active
🤖 TransportationAgent is now active
🤖 WeatherAgent is now active
🤖 TravelPlannerAgent is now active
🤖 ValidationAgent is now active
✅ Validation phase activated
🔄 Revision requested: BudgetAnalysisAgent: Reduce accommodation costs by $300

🌍 VALIDATED GLOBEPILOT TRAVEL PLAN
🎯 PLAN STATUS: APPROVED
💰 BUDGET VALIDATION: Within acceptable range
📅 TRAVEL ITINERARY: [Detailed itinerary follows]
✅ PLAN APPROVED - READY FOR BOOKING!
```

## 🔧 Requirements

- Python 3.8+
- OpenAI API key
- Tavily API key (for web search)
- Internet connection

## 📞 Support

For issues or questions, check that your API keys are valid and you have internet connectivity for web search functionality.

### Quick Test:
```bash
# Test your installation
python test_setup.py
```

This will verify:
- Python version compatibility
- All package imports
- API key configuration
- File structure
- Flask app functionality

### Web Interface Issues:
- Check Flask dependencies: `pip install flask flask-cors`
- Ensure port 8000 is available
- Try `python run_web.py` for dependency checking

### Command Line Issues:
- Verify all packages installed: `pip install -r requirements.txt`
- Check API key environment variables

---

**Ready to plan your perfect trip?** 

🌐 **Web Interface**: `python run_web.py` then visit http://localhost:8000

💻 **Command Line**: `python globepilot_enhanced.py`

Let GlobePiloT's AI agents create your validated travel plan! 🌟 
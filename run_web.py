#!/usr/bin/env python3
"""
Quick start script for GlobePiloT Flask Web Application
"""

import os
import sys

def check_dependencies():
    """Check if required packages are installed"""
    try:
        import flask
        import openai
        import tavily
        print("✅ All required packages found")
    except ImportError as e:
        print(f"❌ Missing package: {e.name}")
        print("Please run: pip install -r requirements.txt")
        sys.exit(1)

def check_api_keys():
    """Check if API keys are set"""
    openai_key = os.getenv('OPENAI_API_KEY')
    tavily_key = os.getenv('TAVILY_API_KEY')
    
    if not openai_key:
        print("⚠️  OPENAI_API_KEY not found in environment variables")
    else:
        print("✅ OpenAI API key found")
        
    if not tavily_key:
        print("⚠️  TAVILY_API_KEY not found in environment variables")
    else:
        print("✅ Tavily API key found")
    
    if not openai_key or not tavily_key:
        print("\n🔑 To set API keys:")
        print("export OPENAI_API_KEY='your-openai-key'")
        print("export TAVILY_API_KEY='your-tavily-key'")
        print("\nOr create a .env file with:")
        print("OPENAI_API_KEY=your-openai-key")
        print("TAVILY_API_KEY=your-tavily-key")

def main():
    print("🌍 GlobePiloT Flask Web Application")
    print("=" * 50)
    
    # Check dependencies
    check_dependencies()
    
    # Check API keys
    check_api_keys()
    
    print("\n🚀 Starting Flask development server...")
    print("📱 Open your browser to: http://localhost:8000")
    print("⏹️  Press Ctrl+C to stop the server")
    print("-" * 50)
    
    # Import and run the Flask app
    try:
        from app import app
        app.run(debug=True, host='0.0.0.0', port=8000)
    except KeyboardInterrupt:
        print("\n👋 GlobePiloT server stopped")
    except Exception as e:
        print(f"\n❌ Error starting server: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 
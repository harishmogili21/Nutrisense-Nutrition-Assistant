#!/usr/bin/env python3
"""
Simple script to run the Nutrisense Nutrition Assistant with Streamlit
"""

import subprocess
import sys
import os

def main():
    """Run the Streamlit app"""
    try:
        # Check if streamlit is installed
        import streamlit
        print("✅ Streamlit is installed")
    except ImportError:
        print("❌ Streamlit not found. Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
    
    # Set Streamlit configuration
    os.environ['STREAMLIT_SERVER_PORT'] = '8501'
    os.environ['STREAMLIT_SERVER_ADDRESS'] = '0.0.0.0'
    
    print("🚀 Starting Nutrisense Nutrition Assistant...")
    print("📱 The app will be available at: http://localhost:8501")
    print("🛑 Press Ctrl+C to stop the server")
    
    # Run the Streamlit app
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", "app.py",
        "--server.port", "8501",
        "--server.address", "0.0.0.0",
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false"
    ])

if __name__ == "__main__":
    main() 
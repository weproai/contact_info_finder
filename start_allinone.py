#!/usr/bin/env python3
"""
All-in-one startup script for App Runner
Starts Ollama and the API in the same container
"""

import os
import sys
import time
import subprocess
import requests
import signal
import threading

def log(message):
    print(f"[STARTUP] {message}", flush=True)

def start_ollama():
    """Start Ollama service in background"""
    log("Starting Ollama service...")
    
    # Start Ollama
    ollama_proc = subprocess.Popen(
        ["ollama", "serve"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for Ollama to be ready
    for i in range(30):
        try:
            response = requests.get("http://localhost:11434/api/tags", timeout=1)
            if response.status_code == 200:
                log("Ollama is ready!")
                return ollama_proc
        except:
            pass
        
        log(f"Waiting for Ollama... ({i+1}/30)")
        time.sleep(2)
    
    log("ERROR: Ollama failed to start!")
    ollama_proc.terminate()
    sys.exit(1)

def ensure_model():
    """Ensure the model is available"""
    model = os.getenv("OLLAMA_MODEL", "gemma:2b")
    log(f"Checking for model: {model}")
    
    try:
        # Check if model exists
        response = requests.get("http://localhost:11434/api/tags")
        models = response.json().get("models", [])
        model_names = [m["name"] for m in models]
        
        if model in model_names or f"{model}:latest" in model_names:
            log(f"Model {model} is already available!")
            return model
        
        # Pull the model
        log(f"Pulling {model} model (this may take a few minutes)...")
        pull_proc = subprocess.run(
            ["ollama", "pull", model],
            capture_output=True,
            text=True
        )
        
        if pull_proc.returncode == 0:
            log(f"Successfully pulled {model}")
            return model
        else:
            log(f"Failed to pull {model}, trying tinyllama as fallback...")
            subprocess.run(["ollama", "pull", "tinyllama"])
            os.environ["OLLAMA_MODEL"] = "tinyllama"
            return "tinyllama"
            
    except Exception as e:
        log(f"Error checking/pulling model: {e}")
        # Continue anyway - fast mode will handle it
        return model

def start_api():
    """Start the FastAPI application"""
    log("Starting API server...")
    
    # Import and run uvicorn
    import uvicorn
    from main import app
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )

def signal_handler(signum, frame):
    """Handle shutdown signals"""
    log("Shutting down...")
    sys.exit(0)

def main():
    """Main startup sequence"""
    log("=== Contact Info Finder All-in-One Startup ===")
    
    # Set up signal handlers
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)
    
    # Ensure localhost is used for Ollama
    os.environ["OLLAMA_BASE_URL"] = "http://localhost:11434"
    
    # Start Ollama
    ollama_proc = start_ollama()
    
    # Ensure model is available
    model = ensure_model()
    log(f"Using model: {model}")
    
    # Start the API (this blocks)
    start_api()

if __name__ == "__main__":
    main()
#!/usr/bin/env python3
"""
Test Ollama connection before deploying to App Runner
"""

import os
import sys
import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_ollama_connection():
    """Test if Ollama server is accessible"""
    base_url = os.getenv('OLLAMA_BASE_URL', 'http://localhost:11434')
    model = os.getenv('OLLAMA_MODEL', 'gemma:2b')
    
    print(f"Testing Ollama connection...")
    print(f"Base URL: {base_url}")
    print(f"Model: {model}")
    
    try:
        # Test server health
        response = requests.get(f"{base_url}/api/tags", timeout=5)
        if response.status_code == 200:
            print("✅ Ollama server is accessible")
            
            # Check if model exists
            models = response.json().get('models', [])
            model_names = [m['name'] for m in models]
            
            if model in model_names or f"{model}:latest" in model_names:
                print(f"✅ Model '{model}' is available")
            else:
                print(f"❌ Model '{model}' not found")
                print(f"Available models: {', '.join(model_names)}")
                return False
                
            # Test generation
            test_prompt = "Extract: John 555-1234"
            gen_response = requests.post(
                f"{base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": test_prompt,
                    "stream": False
                },
                timeout=30
            )
            
            if gen_response.status_code == 200:
                print("✅ Model generation test successful")
                return True
            else:
                print(f"❌ Generation failed: {gen_response.status_code}")
                return False
                
        else:
            print(f"❌ Server returned status: {response.status_code}")
            return False
            
    except requests.exceptions.ConnectionError:
        print(f"❌ Cannot connect to Ollama at {base_url}")
        print("Make sure Ollama is running and accessible")
        return False
    except Exception as e:
        print(f"❌ Error: {e}")
        return False

if __name__ == "__main__":
    success = test_ollama_connection()
    sys.exit(0 if success else 1)
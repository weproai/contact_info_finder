#!/usr/bin/env python
"""
Setup script for Contact Info Finder API
Creates necessary directories and configuration files
"""
import os
import shutil

def create_env_file():
    """Create .env file from template"""
    env_content = """# Ollama Configuration
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2

# ChromaDB Configuration
CHROMA_PERSIST_DIRECTORY=./chroma_db
CHROMA_COLLECTION_NAME=contact_extractions

# API Configuration
API_HOST=0.0.0.0
API_PORT=8000
API_RELOAD=True

# Logging
LOG_LEVEL=INFO
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✓ Created .env file")
    else:
        print("✓ .env file already exists")

def create_directories():
    """Create necessary directories"""
    dirs = ['chroma_db', 'logs']
    for dir_name in dirs:
        if not os.path.exists(dir_name):
            os.makedirs(dir_name)
            print(f"✓ Created {dir_name}/ directory")
        else:
            print(f"✓ {dir_name}/ directory already exists")

def check_dependencies():
    """Check if required dependencies are available"""
    print("\n=== Checking Dependencies ===")
    
    # Check Python packages
    try:
        import fastapi
        print("✓ FastAPI installed")
    except ImportError:
        print("✗ FastAPI not installed - run: pip install -r requirements.txt")
    
    try:
        import ollama
        print("✓ Ollama Python client installed")
    except ImportError:
        print("✗ Ollama client not installed - run: pip install -r requirements.txt")
    
    try:
        import chromadb
        print("✓ ChromaDB installed")
    except ImportError:
        print("✗ ChromaDB not installed - run: pip install -r requirements.txt")
    
    # Check Ollama service
    print("\n=== Checking Ollama Service ===")
    try:
        import requests
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        if response.status_code == 200:
            models = response.json().get('models', [])
            print("✓ Ollama service is running")
            if models:
                print("  Available models:")
                for model in models:
                    print(f"    - {model['name']}")
            else:
                print("  ✗ No models installed. Run: ollama pull llama2")
        else:
            print("✗ Ollama service responded but with error")
    except:
        print("✗ Ollama service not running. Please start Ollama first.")
        print("  Installation: https://ollama.ai")

def main():
    """Run setup"""
    print("Contact Info Finder API Setup")
    print("============================\n")
    
    print("=== Creating Configuration ===")
    create_env_file()
    
    print("\n=== Creating Directories ===")
    create_directories()
    
    check_dependencies()
    
    print("\n=== Setup Complete ===")
    print("\nNext steps:")
    print("1. Create virtual environment: python -m venv venv")
    print("2. Install dependencies: .\\venv\\Scripts\\Activate.ps1 && pip install -r requirements.txt")
    print("3. Start Ollama and pull a model: ollama pull llama2")
    print("4. Run the API: .\\start.ps1")
    print("5. Test the API: python test_api.py")

if __name__ == "__main__":
    main()
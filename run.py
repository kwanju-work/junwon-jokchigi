import subprocess
import sys
import os

# Set Cwd to the directory of run.py
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)

print("=" * 50)
print("junwon jokchigi local development server")
print("=" * 50)

try:
    import fastapi
    import uvicorn
    import httpx
    import dotenv
except ImportError:
    print("Required packages are missing. Installing...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "fastapi", "uvicorn", "httpx", "python-dotenv"])
        print("Installation complete!")
    except Exception as e:
        print(f"Installation failed: {e}")
        print("Please run: pip install fastapi uvicorn httpx python-dotenv")
        sys.exit(1)

print("\nServer is running!")
print("Open your browser and visit:")
print("-> http://127.0.0.1:8000")
print("=" * 50)

# Run uvicorn pointing to api.index:app
subprocess.call([sys.executable, "-m", "uvicorn", "api.index:app", "--host", "127.0.0.1", "--port", "8000"])

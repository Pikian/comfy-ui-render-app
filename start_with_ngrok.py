import os
import subprocess
import threading
import time
import uvicorn
import webbrowser
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
load_dotenv()

def start_ngrok():
    # Get the directory of this script
    script_dir = Path(__file__).parent
    ngrok_path = script_dir / "ngrok.exe"
    
    if not ngrok_path.exists():
        print("ngrok.exe not found. Please download it from https://ngrok.com/download")
        print("and place it in the same directory as this script.")
        return
    
    # Set ngrok authtoken if provided
    ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if ngrok_auth_token:
        print("Setting ngrok authtoken...")
        result = subprocess.run(
            [str(ngrok_path), "config", "add-authtoken", ngrok_auth_token],
            capture_output=True,
            text=True
        )
        if result.returncode != 0:
            print("Error setting authtoken:", result.stderr)
            return
        print("Authtoken set successfully")
    
    print("Starting ngrok tunnel...")
    
    # Start ngrok with web interface
    ngrok_process = subprocess.Popen(
        [str(ngrok_path), "http", "8001", "--log=stdout"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1
    )
    
    print("ngrok process started. Opening web interface...")
    
    # Wait a moment for ngrok to start
    time.sleep(2)
    
    # Open ngrok web interface
    webbrowser.open("http://localhost:4040")
    
    print("\nngrok is running!")
    print("1. Check the web interface at http://localhost:4040 for your public URL")
    print("2. The FastAPI server is running at http://localhost:8001")
    print("3. Press Ctrl+C to stop both servers")
    
    try:
        # Print ngrok output
        while True:
            output = ngrok_process.stdout.readline()
            if output:
                print(output.strip())
            elif ngrok_process.poll() is not None:
                break
            time.sleep(0.1)
    except KeyboardInterrupt:
        print("\nStopping ngrok...")
        ngrok_process.terminate()
        try:
            ngrok_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            ngrok_process.kill()

def start_server():
    uvicorn.run("main:app", host="0.0.0.0", port=8001)

if __name__ == "__main__":
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True
    ngrok_thread.start()
    
    # Start the FastAPI server
    start_server() 
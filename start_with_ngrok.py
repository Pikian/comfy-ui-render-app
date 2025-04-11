import os
from pyngrok import ngrok
import uvicorn
import threading
import time
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def start_ngrok():
    # Set ngrok authtoken if provided
    ngrok_auth_token = os.getenv("NGROK_AUTH_TOKEN")
    if ngrok_auth_token:
        ngrok.set_auth_token(ngrok_auth_token)
    
    # Create ngrok tunnel
    public_url = ngrok.connect(8001)
    print(f"\nPublic URL: {public_url}")
    print("Use this URL to access your middleware from anywhere!")
    
    # Keep the ngrok tunnel open
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ngrok.kill()

def start_server():
    uvicorn.run("main:app", host="0.0.0.0", port=8001)

if __name__ == "__main__":
    # Start ngrok in a separate thread
    ngrok_thread = threading.Thread(target=start_ngrok)
    ngrok_thread.daemon = True
    ngrok_thread.start()
    
    # Start the FastAPI server
    start_server() 
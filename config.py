import os
from pathlib import Path

class Config:
    # Base configuration
    BASE_DIR = Path(__file__).resolve().parent
    OUTPUT_DIR = BASE_DIR / "output"
    
    # ComfyUI configuration
    COMFYUI_HOST = os.getenv("COMFYUI_HOST", "127.0.0.1")
    COMFYUI_PORT = int(os.getenv("COMFYUI_PORT", "8000"))
    COMFYUI_WS_URL = f"ws://{COMFYUI_HOST}:{COMFYUI_PORT}/ws"
    COMFYUI_API_URL = f"http://{COMFYUI_HOST}:{COMFYUI_PORT}"
    
    # Server configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    
    # Supabase configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL", "")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY", "")
    
    # Logging configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration"""
        if not cls.SUPABASE_URL or not cls.SUPABASE_KEY:
            raise ValueError("Supabase credentials are required")
        
        # Create output directory if it doesn't exist
        cls.OUTPUT_DIR.mkdir(exist_ok=True) 
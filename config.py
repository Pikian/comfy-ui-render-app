import os
from dotenv import load_dotenv, find_dotenv

# Force reload of environment variables
load_dotenv(find_dotenv(), override=True)

class Config:
    # RunPod Configuration
    RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
    RUNPOD_ENDPOINT_ID = os.getenv("RUNPOD_ENDPOINT_ID")
    RUNPOD_API_URL = f"https://api.runpod.ai/v2/{RUNPOD_ENDPOINT_ID}"
    RUNPOD_TIMEOUT = int(os.getenv("RUNPOD_TIMEOUT", "300"))
    STATUS_CHECK_INTERVAL = int(os.getenv("STATUS_CHECK_INTERVAL", "5"))
    
    # RunPod Headers
    RUNPOD_HEADERS = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {RUNPOD_API_KEY}"
    }
    
    # Supabase Configuration
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_ROLE_KEY = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
    
    # Server Configuration
    HOST = os.getenv("HOST", "0.0.0.0")
    PORT = int(os.getenv("PORT", "8001"))
    
    # Logging Configuration
    LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
    
    @classmethod
    def validate(cls):
        """Validate required configuration values."""
        required_vars = [
            ("RUNPOD_API_KEY", cls.RUNPOD_API_KEY),
            ("RUNPOD_ENDPOINT_ID", cls.RUNPOD_ENDPOINT_ID),
            ("SUPABASE_URL", cls.SUPABASE_URL),
            ("SUPABASE_KEY", cls.SUPABASE_KEY),
        ]
        
        missing_vars = [var_name for var_name, var_value in required_vars if not var_value]
        
        if missing_vars:
            raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")
            
    @classmethod
    def reload(cls):
        """Reload environment variables."""
        load_dotenv(find_dotenv(), override=True)
        cls.RUNPOD_API_KEY = os.getenv("RUNPOD_API_KEY")
        cls.RUNPOD_HEADERS["Authorization"] = f"Bearer {cls.RUNPOD_API_KEY}" 
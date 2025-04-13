# ComfyUI Middleware

A FastAPI middleware application that connects ComfyUI with frontend applications, handling image generation workflows and Supabase storage integration.

## Features

- Execute ComfyUI workflows asynchronously
- Monitor workflow progress via WebSocket
- Upload generated images to Supabase Storage
- Update Supabase database (`content_requests` table) with status (`ready`/`cancelled`) and image URL
- Public access via ngrok
- Health check endpoint
- Environment-based configuration

## Prerequisites

- Python 3.8+
- ComfyUI running (default port 8188)
- Supabase account with:
    - A project setup
    - A `content_requests` table with `id` (UUID), `status` (TEXT), and `assets` (JSONB) columns.
    - A `media` storage bucket.
    - Your Supabase URL and Service Role Key.
- ngrok account (for public access)

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/comfyui-middleware.git
   cd comfyui-middleware
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   # On Windows
   .\venv\Scripts\activate
   # On Unix/MacOS
   source venv/bin/activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Copy the environment template:
   ```bash
   cp .env.example .env
   ```

5. Update `.env` with your configuration:
   ```env
   # Supabase Configuration
   SUPABASE_URL=your_supabase_url
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key

   # ComfyUI Configuration
   COMFYUI_HOST=127.0.0.1
   COMFYUI_PORT=8188 # Default ComfyUI port

   # Server Configuration
   HOST=0.0.0.0
   PORT=8001

   # ngrok Configuration (optional)
   NGROK_AUTH_TOKEN=your_ngrok_authtoken
   ```

## Running the Application

### Windows
Double-click `start.bat` and choose:
- Option 1: Local access only (http://localhost:8001)
- Option 2: Public access via ngrok (you'll get a public URL)

### Manual Start
```bash
# Make sure venv is activated

# Start locally (with auto-reload for development)
uvicorn main:app --host 0.0.0.0 --port 8001 --reload

# Start with ngrok (runs the server via uvicorn internally)
python start_with_ngrok.py
```

## API Documentation

### Health Check
```http
GET /health
```
Response:
```json
{
  "status": "healthy"
}
```

### Execute Workflow
Initiates the workflow execution in the background.

```http
POST /execute-workflow
Content-Type: application/json

{
  "workflow": {
    // ComfyUI workflow JSON
  },
  "content_request_id": "your_unique_content_request_id" 
}
```

**Immediate Response:**
```json
{
  "status": "processing",
  "message": "Workflow execution started in the background.",
  "content_request_id": "your_unique_content_request_id"
}
```

**Background Process:**

1. The middleware executes the ComfyUI workflow.
2. Monitors progress via WebSocket.
3. On success:
   - Uploads the generated image to Supabase Storage.
   - Updates the corresponding row in the `content_requests` table:
     - Sets `status` to `"ready"`.
     - Updates the `assets` JSONB field with `"image_url"`.
4. On failure:
   - Updates the corresponding row in the `content_requests` table:
     - Sets `status` to `"cancelled"`.

**Frontend Integration:**

The frontend should listen for real-time updates on the `content_requests` table using Supabase subscriptions. When the status changes to `ready` or `cancelled`, or when the `assets` field is updated, the frontend can react accordingly.

## Public Access with ngrok

1. Sign up for a free ngrok account at https://ngrok.com
2. Get your authtoken from the ngrok dashboard
3. Add it to your `.env` file
4. Download `ngrok.exe` (or the appropriate binary for your OS) and place it in the project's root directory.
5. Start the server with ngrok (Option 2 in start.bat or `python start_with_ngrok.py`)
6. Use the provided public URL (shown in the console or at http://localhost:4040) to access your middleware.

## Contributing

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add some amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments

- [ComfyUI](https://github.com/comfyanonymous/ComfyUI)
- [FastAPI](https://fastapi.tiangolo.com/)
- [Supabase](https://supabase.com/)
- [ngrok](https://ngrok.com/) 
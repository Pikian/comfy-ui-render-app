# ComfyUI Middleware

A FastAPI middleware application that connects ComfyUI with frontend applications, handling image generation workflows and Supabase storage integration.

## Features

- Execute ComfyUI workflows
- Monitor workflow progress via WebSocket
- Upload generated images to Supabase
- Public access via ngrok
- Health check endpoint
- Environment-based configuration

## Prerequisites

- Python 3.8+
- ComfyUI running on port 8000
- Supabase account with service role key
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
   COMFYUI_PORT=8000

   # Server Configuration
   HOST=0.0.0.0
   PORT=8001

   # Next.js Callback Configuration
   NEXTJS_CALLBACK_URL=http://localhost:3000/api/comfy-callback
   NEXTJS_API_KEY=your_nextjs_api_key

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
# Start locally
uvicorn main:app --host 0.0.0.0 --port 8001

# Start with ngrok
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
```http
POST /execute-workflow
Content-Type: application/json

{
  "workflow": {
    // ComfyUI workflow JSON
  },
  "content_request_id": "your_unique_id"
}
```

Response:
```json
{
  "workflow_id": "generated_workflow_id"
}
```

### Callback (to your frontend)
When the workflow completes, the server will send a POST request to your configured callback URL:
```json
{
  "status": "completed",
  "image_url": "https://your-supabase-url/storage/v1/object/public/media/comfyui-output/request_id/image.png",
  "content_request_id": "your_request_id"
}
```

## Public Access with ngrok

1. Sign up for a free ngrok account at https://ngrok.com
2. Get your authtoken from the ngrok dashboard
3. Add it to your `.env` file
4. Start the server with ngrok (Option 2 in start.bat)
5. Use the provided public URL to access your middleware

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
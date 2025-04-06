# ComfyUI Trigger App

A FastAPI application that executes ComfyUI workflows and uploads generated images to Supabase.

## Features

- Execute ComfyUI workflows
- Monitor workflow progress
- Upload generated images to Supabase
- Organized storage structure in Supabase
- Environment-based configuration

## Prerequisites

- Python 3.11+
- ComfyUI running locally or remotely
- Supabase account and credentials
- Virtual environment (recommended)

## Local Development Setup

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd comfyui-trigger-app
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

5. Edit `.env` with your configuration:
   - Set ComfyUI host and port
   - Add Supabase credentials
   - Configure server settings

6. Start the server:
   ```bash
   python main.py
   ```

## Docker Deployment

1. Build the Docker image:
   ```bash
   docker build -t comfyui-trigger-app .
   ```

2. Run the container:
   ```bash
   docker run -d \
     -p 8001:8001 \
     -e COMFYUI_HOST=<comfyui-host> \
     -e COMFYUI_PORT=<comfyui-port> \
     -e SUPABASE_URL=<supabase-url> \
     -e SUPABASE_KEY=<supabase-key> \
     comfyui-trigger-app
   ```

## API Usage

### Execute Workflow

```http
POST http://localhost:8001/execute-workflow
Content-Type: application/json

{
    "workflow": {
        // Your ComfyUI workflow JSON
    },
    "content_request_id": "your_request_id"
}
```

### Response

```json
{
    "status": "completed",
    "image_url": "https://your-supabase-url/storage/v1/object/public/media/comfyui-output/request_id/image_uuid.png",
    "content_request_id": "your_request_id",
    "image_uuid": "generated_uuid"
}
```

## Supabase Storage Structure

Images are stored in Supabase with the following structure:
```
comfyui-output/
  ├── {content_request_id}/
  │   └── {image_uuid}.png
```

## Environment Variables

- `COMFYUI_HOST`: ComfyUI server host (default: 127.0.0.1)
- `COMFYUI_PORT`: ComfyUI server port (default: 8000)
- `HOST`: FastAPI server host (default: 0.0.0.0)
- `PORT`: FastAPI server port (default: 8001)
- `SUPABASE_URL`: Your Supabase project URL
- `SUPABASE_KEY`: Your Supabase API key
- `LOG_LEVEL`: Logging level (default: INFO)

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[MIT License](LICENSE) 
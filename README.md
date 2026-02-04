# Gemini API Proxy

A transparent proxy server for Google's Gemini API that hides your API key on the server side.

## Features

- 🔐 **API Key Protection**: Your Gemini API key stays on the server
- 🎫 **Token Authentication**: Simple token-based auth to prevent unauthorized access
- 🚀 **Streaming Support**: Full support for streaming responses (SSE)
- 🔄 **Transparent Proxy**: Forwards requests exactly as-is to Gemini API
- ⚡ **Fast & Async**: Built with FastAPI and httpx for high performance

## Quick Start

### Local Development

1. Clone this repository:
   ```bash
   git clone <your-repo-url>
   cd gemini-proxy
   ```

2. Create a virtual environment and install dependencies:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. Create `.env` file from template:
   ```bash
   cp .env.example .env
   ```

4. Edit `.env` and fill in your values:
   ```
   GEMINI_API_KEY=your_actual_gemini_api_key
   APP_TOKEN=your_secret_token
   ```

5. Run the server:
   ```bash
   uvicorn main:app --reload
   ```

6. Test the health endpoint:
   ```bash
   curl http://localhost:8000/health
   ```

### Deploy to Railway

1. Push this project to a GitHub repository

2. Go to [Railway](https://railway.app/) and create a new project

3. Select "Deploy from GitHub repo" and connect your repository

4. Add environment variables in Railway dashboard:
   - `GEMINI_API_KEY`: Your Gemini API key
   - `APP_TOKEN`: Your secret authentication token

5. Railway will automatically deploy and provide you with a public URL

## API Usage

### Health Check

```bash
GET /health
```

### Proxy Endpoint

All requests to `/v1beta/*` are proxied to Google's Gemini API.

```bash
# Example: Generate content
curl -X POST "https://your-railway-url.railway.app/v1beta/models/gemini-pro:generateContent" \
  -H "Content-Type: application/json" \
  -H "X-App-Token: your_secret_token" \
  -d '{"contents":[{"parts":[{"text":"Hello, Gemini!"}]}]}'
```

### Authentication

Include the `X-App-Token` header in all requests:

```
X-App-Token: your_secret_token
```

## Flutter Integration

Configure your Flutter app to use this proxy:

```bash
flutter run \
  --dart-define=PROXY_BASE_URL=https://your-railway-url.railway.app \
  --dart-define=APP_TOKEN=your_secret_token
```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | Yes | Your Google Gemini API key |
| `APP_TOKEN` | Yes* | Authentication token for client apps |
| `PORT` | No | Server port (default: 8000) |

*If `APP_TOKEN` is not set, authentication is disabled (not recommended for production)

## License

MIT License

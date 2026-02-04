"""
Gemini API Proxy Server

A transparent proxy server that forwards requests to Google's Gemini API
while hiding the API key on the server side.
"""

import json
import logging
import os
from datetime import datetime
from typing import AsyncIterator

import httpx
from fastapi import FastAPI, Request, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, Response

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Configuration from environment variables
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
APP_TOKEN = os.getenv("APP_TOKEN")
GOOGLE_API_BASE = "https://generativelanguage.googleapis.com"

# Debug mode - set to True to see request/response bodies
DEBUG_MODE = os.getenv("DEBUG_MODE", "true").lower() == "true"

app = FastAPI(
    title="Gemini API Proxy",
    description="Transparent proxy for Google Gemini API",
    version="1.0.0",
)

# CORS middleware - allow all origins for mobile apps
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def truncate_string(s: str, max_length: int = 500) -> str:
    """Truncate string for logging."""
    if len(s) <= max_length:
        return s
    return s[:max_length] + f"... [truncated, total {len(s)} chars]"


def verify_token(request: Request) -> None:
    """Verify the app token from request header."""
    if not APP_TOKEN:
        logger.warning("⚠️  APP_TOKEN not set, skipping authentication")
        return
    
    token = request.headers.get("X-App-Token")
    if token != APP_TOKEN:
        logger.warning(f"❌ Invalid token attempt from {request.client.host}")
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing token")


async def stream_response(response: httpx.Response) -> AsyncIterator[bytes]:
    """Stream the response content."""
    async for chunk in response.aiter_bytes():
        yield chunk


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "ok", "service": "gemini-proxy"}


@app.api_route("/v1beta/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
async def proxy_gemini_api(path: str, request: Request):
    """
    Proxy all requests to Google Gemini API.
    
    This endpoint transparently forwards all requests to the Gemini API,
    adding the API key automatically.
    """
    request_id = datetime.now().strftime("%H%M%S%f")[:10]
    
    logger.info(f"{'='*60}")
    logger.info(f"[{request_id}] 📥 Incoming Request")
    logger.info(f"[{request_id}] Method: {request.method}")
    logger.info(f"[{request_id}] Path: /v1beta/{path}")
    logger.info(f"[{request_id}] Client: {request.client.host}")
    
    # Verify token
    verify_token(request)
    
    # Check if API key is configured
    if not GEMINI_API_KEY:
        logger.error(f"[{request_id}] ❌ GEMINI_API_KEY not configured!")
        raise HTTPException(
            status_code=500, 
            detail="Server configuration error: GEMINI_API_KEY not set"
        )
    
    # Build target URL with API key
    target_url = f"{GOOGLE_API_BASE}/v1beta/{path}"
    logger.info(f"[{request_id}] 🎯 Target URL: {target_url}")
    
    # Copy query parameters and add API key
    params = dict(request.query_params)
    params["key"] = GEMINI_API_KEY
    
    # Copy headers (exclude hop-by-hop headers)
    excluded_headers = {"host", "content-length", "transfer-encoding", "connection", "x-app-token"}
    headers = {
        k: v for k, v in request.headers.items() 
        if k.lower() not in excluded_headers
    }
    
    # Get request body
    body = await request.body()
    
    if DEBUG_MODE and body:
        try:
            body_json = json.loads(body)
            body_preview = json.dumps(body_json, ensure_ascii=False, indent=2)
            logger.info(f"[{request_id}] 📤 Request Body Preview:\n{truncate_string(body_preview, 2000)}")
        except Exception:
            logger.info(f"[{request_id}] 📤 Request Body (raw): {truncate_string(body.decode('utf-8', errors='replace'), 500)}")
    
    # Create async client and forward request
    async with httpx.AsyncClient(timeout=300.0) as client:
        try:
            logger.info(f"[{request_id}] 🚀 Forwarding to Google API...")
            
            response = await client.request(
                method=request.method,
                url=target_url,
                params=params,
                headers=headers,
                content=body,
            )
            
            logger.info(f"[{request_id}] 📨 Response Status: {response.status_code}")
            
            content_type = response.headers.get("content-type", "")
            
            # Log response body for errors
            if response.status_code >= 400:
                response_text = response.text
                logger.error(f"[{request_id}] ❌ Error Response (Status {response.status_code}):")
                
                # Try to parse and pretty print JSON error
                try:
                    error_json = json.loads(response_text)
                    logger.error(f"[{request_id}] ❌ Error Details:\n{json.dumps(error_json, indent=2, ensure_ascii=False)}")
                except Exception:
                    logger.error(f"[{request_id}] ❌ Raw Error:\n{response_text}")
            elif DEBUG_MODE:
                response_preview = truncate_string(response.text, 1000)
                logger.info(f"[{request_id}] ✅ Response Preview:\n{response_preview}")
            
            # For streaming responses, use StreamingResponse
            if "text/event-stream" in content_type or "stream" in str(request.url):
                logger.info(f"[{request_id}] 🌊 Streaming response detected")
                # Re-request with streaming
                stream_response_obj = await client.stream(
                    method=request.method,
                    url=target_url,
                    params=params,
                    headers=headers,
                    content=body,
                )
                
                return StreamingResponse(
                    stream_response_obj.aiter_bytes(),
                    status_code=stream_response_obj.status_code,
                    headers={
                        k: v for k, v in stream_response_obj.headers.items()
                        if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
                    },
                    media_type=content_type,
                )
            
            # For non-streaming responses, return directly
            logger.info(f"[{request_id}] ✅ Request completed successfully")
            return Response(
                content=response.content,
                status_code=response.status_code,
                headers={
                    k: v for k, v in response.headers.items()
                    if k.lower() not in {"content-encoding", "content-length", "transfer-encoding"}
                },
                media_type=content_type,
            )
            
        except httpx.TimeoutException:
            logger.error(f"[{request_id}] ⏱️  Timeout error!")
            raise HTTPException(status_code=504, detail="Gateway timeout: Gemini API did not respond in time")
        except httpx.RequestError as e:
            logger.error(f"[{request_id}] 🔥 Request error: {str(e)}")
            raise HTTPException(status_code=502, detail=f"Bad gateway: {str(e)}")


if __name__ == "__main__":
    import uvicorn
    logger.info("🚀 Starting Gemini API Proxy Server")
    logger.info(f"📍 Google API Base: {GOOGLE_API_BASE}")
    logger.info(f"🔑 API Key configured: {'Yes' if GEMINI_API_KEY else 'No'}")
    logger.info(f"🎫 App Token configured: {'Yes' if APP_TOKEN else 'No'}")
    logger.info(f"🐛 Debug mode: {'Enabled' if DEBUG_MODE else 'Disabled'}")
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

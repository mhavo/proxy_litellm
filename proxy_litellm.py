#!/usr/bin/env python3
"""
proxy_litellm.py

Author: Miika Havo <miika.havo@iki.fi>

Description:
    FastAPI-based reverse proxy service for LiteLLM API endpoints. This proxy
    intercepts incoming HTTP requests, appends the configured `app_id` as a
    query parameter, injects custom authentication headers, and forwards the
    request to the LiteLLM server. Responses are returned unchanged to the
    client.

Usage:
    1. Install dependencies in your Python environment (uv env):
       ```bash
       uv pip install fastapi uvicorn httpx python-dotenv
       ```
    2. Create a `.env` file alongside this script with the following keys:
       - LITELLM_BASE_URL (default: https://llm.api.domain.com/v1)
       - DS_APP_ID
       - DS_KEY
       - LITELLM_API_KEY
       - LOG_LEVEL (optional)
       - LOG_FILE (optional)
    3. Launch the proxy:
       ```bash
       uv run uvicorn proxy_litellm:app --host 0.0.0.0 --port 8000
       ```
    4. Configure your client application to send requests to the
       proxy's local address (e.g., http://localhost:8000/v1)
       instead of the original LiteLLM endpoint.

Requirements:
    - Python 3.8+
    - fastapi
    - uvicorn
    - httpx
    - python-dotenv

Last Modified: May 17, 2025
"""

import os
import logging
from fastapi import FastAPI, Request, Response
from dotenv import load_dotenv
import httpx

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Configuration via environment variables
LITELLM_BASE_URL = os.getenv("LITELLM_BASE_URL", "https://llm.api.domain.com/v1")
DS_APP_ID = os.getenv("DS_APP_ID", "")
DS_KEY = os.getenv("DS_KEY", "")
LITELLM_API_KEY = os.getenv("LITELLM_API_KEY", "")

# Custom headers to include in every proxied request
CUSTOM_HEADERS = {}

# Set X-LiteLLM-Key using LITELLM_API_KEY
if LITELLM_API_KEY:
    if not LITELLM_API_KEY.lower().startswith("bearer "):
        CUSTOM_HEADERS["X-LiteLLM-Key"] = f"Bearer {LITELLM_API_KEY}"
    else:
        CUSTOM_HEADERS["X-LiteLLM-Key"] = LITELLM_API_KEY

# Set Authorization using DS_KEY
if DS_KEY:
    CUSTOM_HEADERS["Authorization"] = DS_KEY


# Setup basic logging
LOG_FILE = os.getenv("LOG_FILE", "proxy_litellm.log")
LOG_LEVEL_STR = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_LEVEL_MAP = {
    "DEBUG": logging.DEBUG,
    "INFO": logging.INFO,
    "WARNING": logging.WARNING,
    "ERROR": logging.ERROR,
    "CRITICAL": logging.CRITICAL,
}
LOG_LEVEL = LOG_LEVEL_MAP.get(LOG_LEVEL_STR, logging.INFO)

logging.basicConfig(
    level=LOG_LEVEL,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE),
        logging.StreamHandler(),  # To keep logging to console as well
    ],
)
logger = logging.getLogger(__name__)


@app.get("/")
async def read_root():
    logger.info("Root endpoint / was hit")
    return {
        "message": "Proxy service is running. Use POST /v1 to send requests to LiteLLM."
    }


@app.api_route(
    "/v1{full_path:path}",
    methods=["GET", "POST", "PUT", "DELETE", "PATCH", "OPTIONS", "HEAD"],
)
async def generic_proxy_handler(request: Request, full_path: str):
    """
    Receives a client request, forwards it to the LiteLLM endpoint
    with an added app_id query parameter and custom headers, then returns
    the LiteLLM response directly.
    """
    logger.info(f"Received request: {request.method} {request.url}")
    logger.debug(f"Incoming headers: {request.headers}")
    logger.debug(f"Incoming query params: {request.query_params}")

    # Read incoming body and headers
    body = await request.body()
    logger.debug(
        f"Incoming body: {body.decode(errors='ignore')}"
    )  # Log the body, attempting to decode as text
    incoming_headers = request.headers

    # Build target URL by appending the captured path to the base LiteLLM URL
    target_url = f"{LITELLM_BASE_URL}{full_path}"

    # Prepare query parameters, adding/overriding app_id
    params = dict(request.query_params)
    params["app_id"] = DS_APP_ID

    logger.info(f"Target URL: {target_url}")
    logger.debug(f"Query params to be sent: {params}")

    # Prepare headers for forwarding
    forward_headers = {}
    # Copy non-excluded headers from the original request.
    # Excluded headers are typically hop-by-hop or are managed by the HTTP client (httpx),
    # or are explicitly set by this proxy.
    excluded_header_keys = {  # Using a set for efficient lookup
        "host",
        "content-length",
        "connection",
        "keep-alive",
        "proxy-authenticate",
        "proxy-authorization",
        "te",
        "trailers",
        "transfer-encoding",
        "upgrade",
        "authorization",  # Prevent client's Authorization header from passing through
        "x-litellm-key",  # Prevent client's X-LiteLLM-Key header from passing through
    }
    for key, value in request.headers.items():
        if key.lower() not in excluded_header_keys:
            forward_headers[key] = value

    # Override with CUSTOM_HEADERS. This ensures the proxy's authentication headers are used
    # and take precedence if the client sent conflicting ones (e.g. its own Authorization header).
    forward_headers.update(CUSTOM_HEADERS)

    logger.debug(f"Headers to be sent: {forward_headers}")

    # Forward the request
    try:
        async with httpx.AsyncClient() as client:
            logger.info(
                f"Forwarding {request.method} request to {target_url} with params {params}"
            )
            response = await client.request(
                method=request.method,
                url=target_url,
                params=params,
                headers=forward_headers,
                content=body,
                timeout=30.0,
            )
        logger.info(
            f"Received response from target: {request.method} {target_url} - Status {response.status_code}"
        )
        logger.debug(f"Response headers from target: {response.headers}")
        logger.debug(f"Response content from target: {response.content}")

        # Return the response from LiteLLM as-is
        return Response(
            content=response.content,
            status_code=response.status_code,
            headers=dict(response.headers),
        )
    except httpx.RequestError as exc:
        logger.error(f"An error occurred while requesting {exc.request.url!r}: {exc!r}")
        return Response(content=f"Error proxying request: {exc!r}", status_code=500)
    except Exception as e:
        logger.error(f"An unexpected error occurred: {e!r}")
        return Response(content=f"An unexpected error occurred: {e!r}", status_code=500)

# proxy_litellm

A FastAPI-based reverse proxy for LiteLLM API endpoints.

## Overview

This project provides a reverse proxy service for LiteLLM API endpoints, implemented with FastAPI. The proxy intercepts incoming HTTP requests, appends a configured `app_id` as a query parameter, injects custom authentication headers, and forwards the request to the LiteLLM server. Responses are returned unchanged to the client.

Typical use cases include:

- Centralizing authentication and API key management for LiteLLM.
- Adding or overriding query parameters and headers for all requests.
- Hiding sensitive credentials from client applications.

## Features

- Supports all HTTP methods (GET, POST, PUT, DELETE, PATCH, OPTIONS, HEAD) for `/v1` endpoints.
- Automatically injects authentication headers and `app_id` query parameter.
- Forwards requests and responses transparently.
- Configurable via environment variables.
- Logging to file and console.

## Requirements

- Python 3.8+
- [fastapi](https://fastapi.tiangolo.com/)
- [uvicorn](https://www.uvicorn.org/)
- [httpx](https://www.python-httpx.org/)
- [python-dotenv](https://pypi.org/project/python-dotenv/)

## Installation

1. Clone this repository.

2. Install dependencies (recommended: use [uv](https://github.com/astral-sh/uv)):

   ```bash
   uv pip install fastapi uvicorn httpx python-dotenv
   ```

3. Create a `.env` file in the project directory with the following keys:

   ```
   LITELLM_BASE_URL=https://llm.api.domain.com/v1
   DS_APP_ID=your_app_id
   DS_KEY=your_ds_key
   LITELLM_API_KEY=your_litellm_api_key
   LOG_LEVEL=INFO
   LOG_FILE=proxy_litellm.log
   ```

   - `LITELLM_BASE_URL`: Base URL for the LiteLLM API (default: `https://llm.api.yle.fi/v1`)
   - `DS_APP_ID`: Your application ID (required)
   - `DS_KEY`: Your DS key for authentication (required)
   - `LITELLM_API_KEY`: API key for LiteLLM (required)
   - `LOG_LEVEL`: Logging level (optional, default: INFO)
   - `LOG_FILE`: Log file path (optional, default: `proxy_litellm.log`)

## Usage

Start the proxy server with uvicorn:

```bash
uv run uvicorn proxy_litellm:app --host 0.0.0.0 --port 8000
```

Configure your client application to send requests to the proxy's address (e.g., `http://localhost:8000/v1`) instead of the original LiteLLM endpoint.

## Example

A simple `curl` example:

```bash
curl -X POST "http://localhost:8000/v1/completions" \
     -H "Content-Type: application/json" \
     -d '{"prompt": "Hello, world!", "max_tokens": 10}'
```

The proxy will automatically add the `app_id` and authentication headers before forwarding the request to the LiteLLM API.

## Logging

Logs are written both to the console and to the file specified by `LOG_FILE`. You can adjust the verbosity with the `LOG_LEVEL` environment variable.

## Security

- Do **not** expose this proxy to the public internet without proper access controls.
- Keep your `.env` file secure and never commit it to version control.

## License

MIT License

## Author

Miika Havo (<miika.havo@iki.fi>)

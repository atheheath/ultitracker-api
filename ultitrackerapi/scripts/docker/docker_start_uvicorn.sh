#!/bin/bash
uvicorn ${FASTAPI_MODULE} --host 0.0.0.0 --port ${SERVER_API_PORT} --proxy-headers;

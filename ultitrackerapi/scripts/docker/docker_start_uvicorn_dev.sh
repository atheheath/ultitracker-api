#!/bin/bash
set -e

sleep 5

python /root/ultitrackerapi/scripts/python/initialize_tables.py

uvicorn ${FASTAPI_MODULE} \
    --host 0.0.0.0 \
    --port ${SERVER_API_PORT} \
    --proxy-headers

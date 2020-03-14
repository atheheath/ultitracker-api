#!/bin/bash
uvicorn ${FASTAPI_MODULE} \
    --host 0.0.0.0 \
    --port ${SERVER_API_PORT} \
    --proxy-headers \
    --ssl-keyfile /root/letsencrypt/live/api.ultitracker.com/privkey.pem \
    --ssl-certfile /root/letsencrypt/live/api.ultitracker.com/fullchain.pem

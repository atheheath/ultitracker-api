#!/bin/bash
aws elasticbeanstalk create-environment \
    --application-name ultitracker-api \
    --environment-name ultitracker-api-https-v0-0-4 \
    --tier "Name=WebServer,Type=Standard,Version= " \
    --solution-stack-name "64bit Amazon Linux 2018.03 v2.14.2 running Docker 18.09.9-ce" \
    --version-label https-v0.0.5 \
    --option-settings file://./environment-config-https.json

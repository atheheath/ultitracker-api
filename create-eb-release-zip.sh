#!/bin/bash
rm ../ultitracker-api.zip
zip -r ../ultitracker-api.zip . -x "**/.git/*" ".git/*" "**/config/*" "config/*" "**/letsencrypt/*" "letsencrypt/*"

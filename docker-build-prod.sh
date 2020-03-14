#!/bin/bash

# do this to export variables
# we get from sourcing
set -a
source ./config/prod.env

docker build --tag ultitrackerapi-prod --file prod.dockerfile .

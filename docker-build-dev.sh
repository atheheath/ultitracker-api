#!/bin/bash
cp -r ~/.aws ./.aws

# do this to export variables
# we get from sourcing
set -a
source ./config/dev.env

# start clean everytime
docker-compose --file docker-compose-dev.yml down --volumes

docker-compose --file docker-compose-dev.yml build
# docker build --tag ultitrackerapi-dev --file dev.dockerfile .
rm -rf ./.aws

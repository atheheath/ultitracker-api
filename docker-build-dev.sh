#!/bin/bash
cp -r ~/.aws ./.aws
docker build --tag ultitrackerapi-dev --file dev.dockerfile .
rm -rf ./.aws

#!/bin/bash

set -e

RDS_HOSTNAME=$1
RDS_PASSWORD=$2
SSL_FOLDER=$3

if [[ "${RDS_HOSTNAME}" == "" ]]
then
    echo "Need to pass RDS Hostname as first argument"
    exit 1
fi

if [[ "${RDS_PASSWORD}" == "" ]]
then
    echo "Need to pass RDS Password as second argument"
    exit 1
fi

if [[ "${SSL_FOLDER}" == "" ]]
then
    echo "Need to pass folder containing SSL info as third argument"
    exit 1
fi

# Install docker
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo apt-key add -
sudo add-apt-repository "deb [arch=amd64] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable"

sudo apt-get update
sudo apt-get install -y docker-ce

# Install docker compose
sudo curl -L "https://github.com/docker/compose/releases/download/1.24.1/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Install psql
sudo apt install -y postgresql-client-common
sudo apt install -y postgresql-client-9.5

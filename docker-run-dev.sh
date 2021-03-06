#!/bin/bash
CONFIG_FILE=$1

# # -it option included to be able to Ctrl+C the container
# DEFAULT_ARGS="-it --rm"

# if [[ ${CONFIG_FILE} != "" ]]
# then
#     source ./config/dev.env
#     DEFAULT_ARGS="${DEFAULT_ARGS} --env-file ${CONFIG_FILE}"
# fi

# docker run ${DEFAULT_ARGS} -p ${SERVER_API_PORT}:${SERVER_API_PORT} ultitrackerapi-dev

set -a
source ./config/dev.env

docker-compose --file docker-compose-dev.yml up
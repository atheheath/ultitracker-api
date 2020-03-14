#!/bin/bash
CONFIG_FILE=$1

# -it option included to be able to Ctrl+C the container
DEFAULT_ARGS="-it --rm"

if [[ ${CONFIG_FILE} != "" ]]
then
    source ${CONFIG_FILE}
    DEFAULT_ARGS="${DEFAULT_ARGS} --env-file ${CONFIG_FILE}"
else
    source ./config/prod.env
    DEFAULT_ARGS="${DEFAULT_ARGS} --env-file ./config/prod.env"
fi

docker run ${DEFAULT_ARGS} -p ${SERVER_API_PORT}:${SERVER_API_PORT} ultitrackerapi-prod


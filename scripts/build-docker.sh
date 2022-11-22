#!/bin/bash
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
cd `dirname $SCRIPT_DIR`
export TAG="latest"
if [ "$#" -ge 1 ]; then
    export TAG="$1"
fi
nvidia-docker build \
    --rm \
    -f "./Dockerfile" \
    -t irishandler-python:${TAG} \
    --build-arg "PROJECT_VERSION=${TAG}" \
    "."
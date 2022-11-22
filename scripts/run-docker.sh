SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
PROJECT_DIR=$( dirname ${SCRIPT_DIR} )
export TAG="latest"
if [ "$#" -ge 1 ]; then
    export TAG="$1"
fi
shift 1
set -x
xhost +
docker run \
    -it \
    --rm \
    --user :`id -g` \
    --name="dspip" \
    --gpus="all" \
    --runtime="nvidia" \
    --network="host" \
    --ipc="host" \
    -e TZ="Asia/Jerusalem" \
    -e DISPLAY=$DISPLAY \
    -v /tmp/.X11-unix:/tmp/.X11-unix \
    -v /dev/shm:/dev/shm \
    -v /dev:/dev --device-cgroup-rule='c 81:* rmw' \
    -v /var/run/docker.sock:/var/run/docker.sock \
    -v /usr/bin/docker:/usr/bin/docker \
    -e MODELS_FOLDER=/home/maritime/Graphs/v2.2.0 \
    -e ENV_FOLDER=/home/maritime/Maritime_Demo/run_maritime_V2.2.0/ENV \
    -v /home/maritime/Maritime_Demo/run_maritime_V2.2.0/ENV:/home/maritime/Maritime_Demo/run_maritime_V2.2.0/ENV \
    -v ${PROJECT_DIR}/configs:/app/irishandler-python/configs \
    -v ${PROJECT_DIR}/storage:/app/irishandler-python/storage \
    irishandler-python:$TAG $@

# -e ENV_FOLDER=/app/irishandler-python/ENV \
# -v /home/maritime/Maritime_Demo/run_maritime_V2.2.0/ENV:/app/irishandler-python/ENV \
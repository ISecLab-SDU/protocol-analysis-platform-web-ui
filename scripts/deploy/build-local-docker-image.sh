#!/bin/bash

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
LOG_FILE=${SCRIPT_DIR}/build-local-docker-image.log
ERROR=""
IMAGE_NAME="vben-admin-local"
PROXY_HOST="127.0.0.1"
PROXY_PORT="63333"
PROXY_ARGS=()

function is_port_open() {
    local host=$1
    local port=$2

    if command -v nc >/dev/null 2>&1; then
        nc -z "${host}" "${port}" >/dev/null 2>&1
        return $?
    elif command -v python3 >/dev/null 2>&1; then
        python3 - "${host}" "${port}" <<'PY'
import socket
import sys

host = sys.argv[1]
port = int(sys.argv[2])

with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
    sock.settimeout(1.0)
    try:
        sock.connect((host, port))
    except OSError:
        sys.exit(1)
sys.exit(0)
PY
        return $?
    else
        bash -c "echo >/dev/tcp/${host}/${port}" >/dev/null 2>&1
        return $?
    fi
}

function prepare_proxy_args() {
    if is_port_open "${PROXY_HOST}" "${PROXY_PORT}"; then
        local proxy_url="http://${PROXY_HOST}:${PROXY_PORT}"
        echo "Info: Detected proxy at ${proxy_url}; docker build will use this proxy"
        PROXY_ARGS=(
            --network=host
            --build-arg "HTTP_PROXY=${proxy_url}"
            --build-arg "HTTPS_PROXY=${proxy_url}"
            --build-arg "http_proxy=${proxy_url}"
            --build-arg "https_proxy=${proxy_url}"
        )
    else
        echo "Info: Proxy ${PROXY_HOST}:${PROXY_PORT} not available; continuing without proxy"
        PROXY_ARGS=()
    fi
}

function stop_and_remove_container() {
    # Stop and remove the existing container
    docker stop ${IMAGE_NAME} >/dev/null 2>&1
    docker rm ${IMAGE_NAME} >/dev/null 2>&1
}

function remove_image() {
    # Remove the existing image
    docker rmi vben-admin-pro >/dev/null 2>&1
}

function install_dependencies() {
    # Install all dependencies
    cd ${SCRIPT_DIR}
    pnpm install || ERROR="install_dependencies failed"
}

function build_image() {
    # build docker
    prepare_proxy_args
    docker build "${PROXY_ARGS[@]}" -f Dockerfile -t ${IMAGE_NAME} ../../ || ERROR="build_image failed"
}

function log_message() {
    if [[ ${ERROR} != "" ]];
    then
        >&2 echo "build failed, Please check build-local-docker-image.log for more details"
        >&2 echo "ERROR: ${ERROR}"
        exit 1
    else
        echo "docker image with tag '${IMAGE_NAME}' built sussessfully. Use below sample command to run the container"
        echo ""
        echo "docker run -d -p 8010:8080 --name ${IMAGE_NAME} ${IMAGE_NAME}"
    fi
}

echo "Info: Stopping and removing existing container and image" | tee ${LOG_FILE}
stop_and_remove_container
remove_image

echo "Info: Installing dependencies" | tee -a ${LOG_FILE}
install_dependencies 1>> ${LOG_FILE} 2>> ${LOG_FILE}

if [[ ${ERROR} == "" ]]; then
    echo "Info: Building docker image" | tee -a ${LOG_FILE}
    build_image 1>> ${LOG_FILE} 2>> ${LOG_FILE}
fi

log_message | tee -a ${LOG_FILE}

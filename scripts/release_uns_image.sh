#!/bin/bash

echo "releaseing image..."

DOCKER_REGISTRY="registry.thetaphi.dev"
TAG="latest"
IMAGE_NAME="uns"
CONTAINER_NAME="uns-dev"
CONTAINER_PORT=8000
HOST_PORT=8000

# Optional env file (default: .env at repo root)
ENV_FILE=${ENV_FILE:-.env.test}

docker build -t $IMAGE_NAME .

# check and exit if build failed
if [ $? -ne 0 ]; then
    echo "Docker image $IMAGE_NAME build failed."
    read -p "Press any key to finish..."
    exit 1
fi

# Print a message indicating the build is complete
echo "Docker image $IMAGE_NAME built successfully."

echo "Running in test mode. Will stream logs; release only if you confirm."
# stop and remove the existing container if it exists
if [ "$(docker ps -q -f name=$CONTAINER_NAME)" ]; then
    echo "stopping and removing existing container $CONTAINER_NAME..."
    docker stop $CONTAINER_NAME
    docker rm $CONTAINER_NAME
fi
# run the container
echo "running container $CONTAINER_NAME..."
if [ -f "$ENV_FILE" ]; then
    echo "loading environment from $ENV_FILE"
    docker run --network uns-dev-proxy -d --env-file "$ENV_FILE" -p $HOST_PORT:$CONTAINER_PORT --name $CONTAINER_NAME $IMAGE_NAME 
else
    echo "no env file found at $ENV_FILE; running without --env-file"
    docker run --network uns-dev-proxy -d -p $HOST_PORT:$CONTAINER_PORT --name $CONTAINER_NAME $IMAGE_NAME 
fi
echo "Docker container for $IMAGE_NAME:$TAG is running on port $HOST_PORT."
echo "Streaming logs. Press Ctrl+C to stop following logs and decide on release."

# Allow Ctrl+C to break out of logs without exiting the script
trap 'echo; echo "Stopping log stream..."; ' INT
docker logs -f $CONTAINER_NAME || true
trap - INT

echo
read -rp "Type 'release' to push $IMAGE_NAME:$TAG to $DOCKER_REGISTRY (Enter to skip): " ANSWER
if [ "$ANSWER" = "release" ]; then
    echo "Releasing image to $DOCKER_REGISTRY..."
    docker tag $IMAGE_NAME $DOCKER_REGISTRY/$IMAGE_NAME:$TAG
    if docker push $DOCKER_REGISTRY/$IMAGE_NAME:$TAG; then
        echo "Image pushed successfully to $DOCKER_REGISTRY/$IMAGE_NAME:$TAG."
    else
        echo "Failed to push the image to $DOCKER_REGISTRY."
        read -p "Press any key to finish..."
        exit 1
    fi
else
    echo "Skipping release."
fi
echo "Stopping and removing test container $CONTAINER_NAME..."
docker stop $CONTAINER_NAME
docker rm $CONTAINER_NAME

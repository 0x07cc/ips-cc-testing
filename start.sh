#!/bin/bash
# ips-cc Testing Environment container startup script

# If a container with the ips-test-environment image already exists
if sudo docker ps -a | grep ips-test-environment >/dev/null; then
        container=$(docker ps -a | grep -m 1 ips-test-environment | awk '{split($0,a," "); print a[1]}')
        echo "Starting an existing container: " $container
        sudo docker start -ai $container
else
        # First time
        echo "Starting a new container"
        sudo docker container run --cap-add=NET_ADMIN --cap-add=NET_RAW -ti ips-test-environment
fi

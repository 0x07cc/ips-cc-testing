#!/bin/bash
docker container run --cap-add=NET_ADMIN --cap-add=NET_RAW -ti ips-test-environment /usr/bin/git -C /root/ips-cc/ pull --ff-only

#!/bin/bash
docker container run --cap-add=NET_ADMIN --cap-add=NET_RAW -ti ips-test-environment /usr/bin/env python3 /root/test.py

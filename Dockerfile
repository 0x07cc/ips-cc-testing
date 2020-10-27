FROM debian:latest
RUN apt update
RUN apt install -y python3 git build-essential libnetfilter-queue-dev python3-setuptools python3-distutils python3-dev iptables netcat python3-requests nano
RUN git clone https://github.com/kti/python-netfilterqueue /root/python-netfilterqueue
RUN git clone https://github.com/0x07cc/ips-cc /root/ips-cc
RUN cd /root/python-netfilterqueue/ ; python3 setup.py install
COPY docker-scripts/test.py /root/
COPY docker-scripts/entrypoint.py /root/
CMD /usr/bin/env python3 /root/entrypoint.py

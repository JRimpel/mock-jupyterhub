#!/usr/bin/env bash
docker run -t --rm -d --name xdmod -p 8443:443 tools-ext-01.ccr.xdmod.org/xdmod:x86_64-rockylinux8.10.20240528-v11.0.2-3-01 /bin/bash
docker exec xdmod openssl genrsa -out /etc/pki/tls/private/localhost.key -rand /proc/cpuinfo:/proc/filesystems:/proc/interrupts:/proc/ioports:/proc/uptime 2048
docker exec xdmod /usr/bin/openssl req -new -key /etc/pki/tls/private/localhost.key -x509 -sha256 -days 365 -set_serial $RANDOM -extensions v3_req -out /etc/pki/tls/certs/localhost.crt -subj "/C=XX/L=Default City/O=Default Company Ltd"
docker cp ~/xdmod/ xdmod:/root/xdmod
docker exec -w /root/xdmod xdmod composer install
docker exec -w /root/xdmod xdmod /root/bin/buildrpm xdmod
docker exec -e XDMOD_TEST_MODE="fresh_install" xdmod /root/xdmod/tests/ci/bootstrap.sh

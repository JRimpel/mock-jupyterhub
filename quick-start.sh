xdmod_container="xdmod"

docker cp ../xdmod/html/gui/js/PortalModule.js $xdmod_container:usr/share/xdmod/html/gui/js/PortalModule.js
docker cp ../xdmod/html/gui/js/modules/metric_explorer/MetricExplorer.js $xdmod_container:usr/share/xdmod/html/gui/js/modules/metric_explorer/MetricExplorer.js

docker exec $xdmod_container bash -c "cat >> /etc/xdmod/portal_settings.ini <<'EOF'

[jupyterhub]
url = \"/jupyter/\"
EOF"

docker exec $xdmod_container bash -c '/root/bin/services restart'
docker exec $xdmod_container mkdir -p /etc/xdmod/keys
docker exec $xdmod_container bash -c "ln -s /run/secrets/xdmod-private.pem /etc/xdmod/keys/xdmod-private.pem"
docker exec --user root $xdmod_container chmod 664 /etc/xdmod/keys/xdmod-private.pem


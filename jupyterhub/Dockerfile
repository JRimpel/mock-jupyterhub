FROM jupyterhub

RUN apt-get update && apt-get install -y python3-dev

RUN python3 -m pip install --no-cache-dir dockerspawner

COPY jupyterhub/xdmodauthenticator /tmp/jupyterhub/xdmodauthenticator
RUN python3 -m pip install -e /tmp/jupyterhub/xdmodauthenticator

COPY --chmod=u+x jwt-service/jwt-service.py /usr/bin/jwt-service.py

CMD jupyterhub -f /srv/jupyterhub/jupyterhub_config.py

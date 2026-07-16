FROM jupyterhub

RUN apt-get update && apt-get install -y python3-dev

RUN python3 -m pip install --no-cache-dir dockerspawner

COPY xdmodauthenticator /srv/jupyterhub/xdmodauthenticator
RUN python3 -m pip install -e /srv/jupyterhub/xdmodauthenticator

CMD jupyterhub -f /srv/jupyterhub/jupyterhub_config.py

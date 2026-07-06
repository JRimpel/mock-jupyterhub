FROM jupyterhub
RUN apt-get update && apt-get install -y python3-dev
RUN python3 -m pip install --no-cache-dir dockerspawner
CMD jupyterhub -f /srv/jupyterhub/jupyterhub_config.py

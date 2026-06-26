FROM python:3.11
RUN apt-get update && apt-get install -y vim
RUN python -m pip install tornado python-jose

COPY ./jwt-server.py /usr/local/bin/

CMD python3 -u /usr/local/bin/jwt-server.py

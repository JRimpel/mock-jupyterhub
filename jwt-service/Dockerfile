FROM python:3.11

RUN python -m pip install tornado python-jose

COPY ./jwt-server.py /usr/local/bin/

CMD jwt-server.py

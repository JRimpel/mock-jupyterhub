FROM python:3.11
RUN python3 -m pip install tornado
RUN python3 -m pip install jupyterhub
COPY ./chart-service.py /usr/local/bin/

CMD python3 -u /usr/local/bin/chart-service.py

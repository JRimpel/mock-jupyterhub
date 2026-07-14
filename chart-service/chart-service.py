import os
from urllib.parse import urlparse
from tornado.httpserver import HTTPServer
from tornado.httpclient import AsyncHTTPClient
from tornado.web import Application, HTTPError, RequestHandler, authenticated
from tornado.ioloop import IOLoop
from jupyterhub.services.auth import HubOAuthenticated, HubOAuthCallbackHandler
import requests
import json


def event_stream(session, url):
    """Generator yielding events from a JSON event stream

    For use with the server progress API
    """
    r = session.get(url, stream=True)
    r.raise_for_status()
    for line in r.iter_lines():
        line = line.decode('utf8', 'replace')
        # event lines all start with `data:`
        # all other lines should be ignored (they will be empty)
        if line.startswith('data:'):
            yield json.loads(line.split(':', 1)[1])
def start_server(session, hub_url, user, server_name=""):
    """Start a server for a jupyterhub user

    Returns the full URL for accessing the server
    """
    user_url = f"{hub_url}/jupyter/hub/api/users/{user}"
    log_name = f"{user}/{server_name}".rstrip("/")

    # step 1: get user status
    r = session.get(user_url)
    r.raise_for_status()
    user_model = r.json()

    # if server is not 'active', request launch
    if server_name not in user_model.get('servers', {}):
        # log.info(f"Starting server {log_name}")
        r = session.post(f"{user_url}/servers/{server_name}")
        r.raise_for_status()
        r = session.get(user_url)
        r.raise_for_status()
        user_model = r.json()

    # report server status
    server = user_model['servers'][server_name]
    if server['pending']:
        status = f"pending {server['pending']}"
    elif server['ready']:
        status = "ready"
    else:
        # shouldn't be possible!
        raise ValueError(f"Unexpected server state: {server}")

    # wait for server to be ready using progress API
    progress_url = user_model['servers'][server_name]['progress_url']
    for event in event_stream(session, f"{hub_url}{progress_url}"):
        if event.get("ready"):
            server_url = event['url']
            break
    else:
        # server never ready
        raise ValueError(f"{log_name} never started!")

    # at this point, we know the server is ready and waiting to receive requests
    # return the full URL where the server can be accessed
    return server_url


class ChartServiceHandler(HubOAuthenticated, RequestHandler):
    def initialize(self):
        self.hub_auth.hub_prefix = '/jupyter'
        self.hub_auth.oauth_client_id = 'service-chart-service'
        self.hub_auth.oauth_redirect_uri = '/jupyter/services/chart-service/oauth_callback/'
        self.hub_auth.api_url = 'http://jupyterhub:8000/jupyter/hub/api/'
        self.hub_host = 'http://jupyterhub:8000'
        self.config = {}
    @authenticated
    def get(self):
        token = self.hub_auth.get_token(self)
        user =  self.get_current_user()
        session = requests.Session()
        session.headers = {"Authorization": f"token {token}"}
        notebook = self.get_argument('notebook')
        # chart_title = self.get_argument('title')
        server_url = start_server(session, self.hub_host,user.get('name'))  
        test = notebook_generation()
        response = session.put(f'{self.hub_host}{server_url}api/contents/test-title',headers={'Content-Type': 'application/json'}, json={
            'content': test,
            'type': 'notebook',
        })
        print(response, flush=True)
        print(response.status_code, flush=True)
        print(response.json(), flush=True)
        self.redirect(server_url)
    def post(self):
        data = json.loads(self.request.body)
        self.config = data
        print(self.config, flush=True)      
        self.write('Data Received')

 #'/rest/auth/jwt-redirect'    
        
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')    
    def options(self, *args):
        # no body
        # `*args` is for route with `path arguments` supports
        self.set_status(204)
        self.finish()        

def notebook_generation():
    notebook = {
                "metadata": {
                    "kernel_info": {
                        "name": "Python 3"
                    },
                    "language_info": {
                        "name": "Python",
                        "version": "the version of the language",
                        "codemirror_mode": "The name of the codemirror mode to use [optional]",
                    },
                },
                "nbformat": 4,
                "nbformat_minor": 0,
                "cells": [
                    {
                "cell_type" : 'markdown',
                "metadata" : {},
                "source" : 'text'
                    }
                ]
            }
    return notebook


def main():
    application = Application([('/jupyter/services/chart-service', ChartServiceHandler), 
                               ('/jupyter/services/chart-service/oauth_callback/', HubOAuthCallbackHandler)],
                              cookie_secret=os.urandom(32), debug=True)
    http_server = HTTPServer(application)
    url = urlparse('http://0.0.0.0:2323')
    http_server.listen(url.port, url.hostname)
    IOLoop.current().start()
if __name__ == '__main__':
    main()

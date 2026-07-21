#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
from jose import jwt
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, HTTPError, RequestHandler
from jupyterhub.services.auth import HubAuthenticated

JWT_EXPIRATION_MINUTES = 5

class JWTServiceHandler(HubAuthenticated, RequestHandler):

    def get(self):
        auth_header = self.request.headers.get('Authorization', None)
        if not auth_header:
            raise HTTPError(401, 'Missing Authorization header.')

        jupyterhub_api_token = auth_header.split()[1]
        jupyterhub_user = self.hub_auth.user_for_token(jupyterhub_api_token, use_cache=False)

        if not jupyterhub_user:
            raise HTTPError(401, 'Invalid JupyterHub API token.')

        username = jupyterhub_user['name']
        token = self.create_token(username)
        self.write(token)

    def create_token(self, username):
        claims_set = {
            'sub': username,
            'exp': datetime.now() + timedelta(minutes=JWT_EXPIRATION_MINUTES)
        }
        with open('/run/secrets/jwt-private-key', 'r') as private_key_file:
            return jwt.encode(
                claims_set,
                private_key_file.read(),
                algorithm='RS256'
            )

def main():
    application = Application([('/jupyter/services/jwt-service', JWTServiceHandler)],debug=True)

    http_server = HTTPServer(application)
    url = urlparse('http://localhost:9888')

    http_server.listen(url.port, url.hostname)
    IOLoop.current().start()

if __name__=='__main__':
    main()

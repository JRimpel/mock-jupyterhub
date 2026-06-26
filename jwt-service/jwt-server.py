#!/usr/bin/env python3

import os
from datetime import datetime, timedelta
from urllib.parse import urlparse
from jose import jwt
from tornado.httpserver import HTTPServer
from tornado.ioloop import IOLoop
from tornado.web import Application, HTTPError, RequestHandler


JWT_EXPIRATION_MINUTES = 5

class JWTServiceHandler(RequestHandler):

    def get(self):
        token = self.create_token('admin')
        print('TOKEN CREATED AND RETURNING')
        self.write(token)

    def create_token(self, username):
        print('CREATING TOKEN...')
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
    print('main opened')
    application = Application([('/', JWTServiceHandler)],debug=True)

    http_server = HTTPServer(application)
    url = urlparse('http://0.0.0.0:9888')

    http_server.listen(url.port, url.hostname)
    print('server running')
    IOLoop.current().start()

if __name__=='__main__':
    main()


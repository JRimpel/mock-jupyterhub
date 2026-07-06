from urllib.parse import urlparse
from tornado.httpserver import HTTPServer
from tornado.web import Application, HTTPError, RequestHandler
from tornado.ioloop import IOLoop

class ChartServiceHandler(RequestHandler):
    def get(self):
        self.write('reponse')
    def post(self):
        data = self.request.body
        self.write(f'\nEcho: {data}')
    def set_default_headers(self):
        self.set_header("Access-Control-Allow-Origin", "*")
        self.set_header("Access-Control-Allow-Headers", "x-requested-with")
        self.set_header('Access-Control-Allow-Methods', 'POST, GET, OPTIONS')    
    def options(self, *args):
        # no body
        # `*args` is for route with `path arguments` supports
        self.set_status(204)
        self.finish()        
def main():
    application = Application([('/jupyter/services/chart-service/', ChartServiceHandler)], debug=True)
    http_server = HTTPServer(application)
    url = urlparse('http://0.0.0.0:2323')
    http_server.listen(url.port, url.hostname)
    IOLoop.current().start()
if __name__ == '__main__':
    main()

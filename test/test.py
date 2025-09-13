from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import os

class HeaderTestHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        all_headers = dict(self.headers)
        auth_headers = {k: v for k, v in all_headers.items() if k.lower().startswith('x-auth-')}
        proxy_headers = {
            'X-Real-IP': all_headers.get('X-Real-IP'),
            'X-Forwarded-For': all_headers.get('X-Forwarded-For'),
            'X-Forwarded-Proto': all_headers.get('X-Forwarded-Proto'),
            'Host': all_headers.get('Host'),
            'CF-Access-JWT-Assertion': all_headers.get('CF-Access-JWT-Assertion')
        }
        
        response_data = {
            'status': 'OK',
            'message': 'CFTL Header Test Endpoint',
            'auth_headers': auth_headers,
            'proxy_headers': {k: v for k, v in proxy_headers.items() if v},
            'all_headers': all_headers
        }
        
        self.wfile.write(json.dumps(response_data, indent=2).encode())
    
    def do_POST(self):
        self.do_GET()
    
    def log_message(self, format, *args):
        pass

port = int(os.environ.get('PORT', '3000'))
server = HTTPServer(('0.0.0.0', port), HeaderTestHandler)
server.serve_forever()
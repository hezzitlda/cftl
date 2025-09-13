#!/usr/bin/env python3
"""
CF Zero Trust Third Layer - Authentication Server
"""

from http.server import HTTPServer, BaseHTTPRequestHandler
import jwt
import json
import os
import sys

PORT = int(os.environ.get('AUTH_PORT', '9999'))
VERBOSE = os.environ.get('VERBOSE', 'false').lower() == 'true'
CONFIG_FILE = '/tmp/auth_config.json'

AUTH_CONFIGS = {}

def load_auth_configs():
    """Load auth configs"""
    global AUTH_CONFIGS
    
    if not os.path.exists(CONFIG_FILE):
        print(f"[CFTL-AUTH] WARNING: No config file - bypass mode", flush=True)
        return
    
    try:
        with open(CONFIG_FILE, 'r') as f:
            AUTH_CONFIGS = json.load(f)
    except Exception as e:
        print(f"[CFTL-AUTH] ERROR loading config: {e}", flush=True)
        AUTH_CONFIGS = {}

class ThirdLayerAuthHandler(BaseHTTPRequestHandler):
    """HTTP handler"""
    
    def do_GET(self):
        service_name = self.headers.get('X-Service-Name', '')
        
        if service_name not in AUTH_CONFIGS:
            token = self.headers.get('CF-Access-JWT-Assertion')
            if token:
                try:
                    decoded = jwt.decode(token, options={"verify_signature": False})
                    token_email = decoded.get('email', '')
                    token_sub = decoded.get('sub', '')
                    token_country = decoded.get('country', '')
                    
                    self.send_response(200)
                    if token_email:
                        self.send_header('X-Auth-User-Email', token_email)
                    if token_sub:
                        self.send_header('X-Auth-User-ID', token_sub)
                    if token_country:
                        self.send_header('X-Auth-User-Country', token_country)
                    self.send_header('X-Auth-Method', 'cf-access-bypass')
                    self.end_headers()
                except:
                    self.send_response(200)
                    self.end_headers()
            else:
                self.send_response(200)
                self.end_headers()
            return
        
        config = AUTH_CONFIGS[service_name]
        token = self.headers.get('CF-Access-JWT-Assertion')
        
        if not token:
            print(f"[CFTL-AUTH] DENIED: No CF Access token for {service_name}", flush=True)
            self.send_response(401)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Third Layer: CF Access token required')
            return
        
        try:
            decoded = jwt.decode(token, options={"verify_signature": False})
            token_aud = decoded.get('aud', [''])[0] if isinstance(decoded.get('aud'), list) else decoded.get('aud')
            token_email = decoded.get('email', '').lower()
            token_sub = decoded.get('sub', '')
            token_country = decoded.get('country', '')
            token_iss = decoded.get('iss', '')
            token_type = decoded.get('type', '')
            token_identity_nonce = decoded.get('identity_nonce', '')
            
            if token_aud != config['aud']:
                print(f"[CFTL-AUTH] DENIED: AUD mismatch for {service_name}", flush=True)
                self.send_response(401)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Third Layer: Invalid AUD')
                return
            
            if config.get('emails') and token_email not in config['emails']:
                print(f"[CFTL-AUTH] DENIED: Unauthorized email for {service_name}: {token_email}", flush=True)
                self.send_response(403)
                self.send_header('Content-Type', 'text/plain')
                self.end_headers()
                self.wfile.write(b'Third Layer: Email not authorized')
                return
            
            self.send_response(200)
            self.send_header('X-Auth-User-Email', token_email)
            self.send_header('X-Auth-User-ID', token_sub)
            
            if token_country:
                self.send_header('X-Auth-User-Country', token_country)
            if token_iss:
                self.send_header('X-Auth-Issuer', token_iss)
            if token_type:
                self.send_header('X-Auth-Token-Type', token_type)
            if token_identity_nonce:
                self.send_header('X-Auth-Identity-Nonce', token_identity_nonce)
            
            self.send_header('X-Auth-Method', 'cf-access-third-layer')
            self.send_header('X-Auth-Service', service_name)
            self.send_header('X-Auth-AUD', token_aud)
            self.end_headers()
            
        except jwt.DecodeError as e:
            print(f"[CFTL-AUTH] DENIED: Invalid JWT for {service_name}: {e}", flush=True)
            self.send_response(401)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Third Layer: Invalid token format')
        
        except Exception as e:
            print(f"[CFTL-AUTH] ERROR: {e}", flush=True)
            self.send_response(500)
            self.send_header('Content-Type', 'text/plain')
            self.end_headers()
            self.wfile.write(b'Third Layer: Internal error')
    
    def log_message(self, format, *args):
        if "401" in str(args) or "403" in str(args) or "500" in str(args):
            print(f"[CFTL-HTTP] {format%args}", flush=True)

if __name__ == '__main__':
    load_auth_configs()
    server = HTTPServer(('127.0.0.1', PORT), ThirdLayerAuthHandler)
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print(f"\n[CFTL-AUTH] Shutting down...", flush=True)
        server.shutdown()
#!/usr/bin/env python3
"""
CF Zero Trust Third Layer - Authentication Server
"""

from aiohttp import web
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

async def handle_auth(request):
    """Handle authentication request"""
    service_name = request.headers.get('X-Service-Name', '')
    
    # If no config for this service, check for CF Access token and bypass
    if service_name not in AUTH_CONFIGS:
        token = request.headers.get('CF-Access-JWT-Assertion')
        if token:
            try:
                decoded = jwt.decode(token, options={"verify_signature": False})
                token_email = decoded.get('email', '')
                token_sub = decoded.get('sub', '')
                token_country = decoded.get('country', '')
                
                headers = {'X-Auth-Method': 'cf-access-bypass'}
                if token_email:
                    headers['X-Auth-User-Email'] = token_email
                if token_sub:
                    headers['X-Auth-User-ID'] = token_sub
                if token_country:
                    headers['X-Auth-User-Country'] = token_country
                
                return web.Response(headers=headers)
            except:
                return web.Response()
        else:
            return web.Response()
    
    # Service has config, validate
    config = AUTH_CONFIGS[service_name]
    token = request.headers.get('CF-Access-JWT-Assertion')
    
    if not token:
        print(f"[CFTL-AUTH] DENIED: No CF Access token for {service_name}", flush=True)
        return web.Response(text='Third Layer: CF Access token required', status=401)
    
    try:
        decoded = jwt.decode(token, options={"verify_signature": False})
        token_aud = decoded.get('aud', [''])[0] if isinstance(decoded.get('aud'), list) else decoded.get('aud')
        token_email = decoded.get('email', '').lower()
        token_sub = decoded.get('sub', '')
        token_country = decoded.get('country', '')
        token_iss = decoded.get('iss', '')
        token_type = decoded.get('type', '')
        token_identity_nonce = decoded.get('identity_nonce', '')
        
        # Validate AUD
        if token_aud != config['aud']:
            print(f"[CFTL-AUTH] DENIED: AUD mismatch for {service_name}", flush=True)
            return web.Response(text='Third Layer: Invalid AUD', status=401)
        
        # Validate email if configured
        if config.get('emails') and token_email not in config['emails']:
            print(f"[CFTL-AUTH] DENIED: Unauthorized email for {service_name}: {token_email}", flush=True)
            return web.Response(text='Third Layer: Email not authorized', status=403)
        
        # Build success response with headers
        headers = {
            'X-Auth-User-Email': token_email,
            'X-Auth-User-ID': token_sub,
            'X-Auth-Method': 'cf-access-third-layer',
            'X-Auth-Service': service_name,
            'X-Auth-AUD': token_aud
        }
        
        if token_country:
            headers['X-Auth-User-Country'] = token_country
        if token_iss:
            headers['X-Auth-Issuer'] = token_iss
        if token_type:
            headers['X-Auth-Token-Type'] = token_type
        if token_identity_nonce:
            headers['X-Auth-Identity-Nonce'] = token_identity_nonce
        
        return web.Response(headers=headers)
        
    except jwt.DecodeError as e:
        print(f"[CFTL-AUTH] DENIED: Invalid JWT for {service_name}: {e}", flush=True)
        return web.Response(text='Third Layer: Invalid token format', status=401)
    
    except Exception as e:
        print(f"[CFTL-AUTH] ERROR: {e}", flush=True)
        return web.Response(text='Third Layer: Internal error', status=500)

async def init_app():
    """Initialize application"""
    load_auth_configs()
    
    app = web.Application()
    app.router.add_get('/', handle_auth)
    
    return app

def main():
    """Main entry point"""
    app = init_app()
    
    try:
        web.run_app(
            app,
            host='127.0.0.1',
            port=PORT,
            print=None,
            access_log=None
        )
    except KeyboardInterrupt:
        print(f"\n[CFTL-AUTH] Shutting down...", flush=True)

if __name__ == '__main__':
    main()

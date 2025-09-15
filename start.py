#!/usr/bin/env python3
"""
CF Zero Trust Third Layer - Main Orchestration Script
Starts all components of the third layer protection system
"""

import os
import sys
import subprocess
import signal
import time
import random
from config import parse_services_env, generate_nginx_config, save_auth_config

# Running processes
processes = []

def cleanup(signum=None, frame=None):
    """Clean shutdown of all third layer components"""
    print("\n[CFTL] Shutting down all third layer services...", flush=True)
    
    for proc in processes:
        try:
            proc.terminate()
            proc.wait(timeout=5)
        except:
            try:
                proc.kill()
            except:
                pass
    
    sys.exit(0)

def find_free_port():
    """Find a random free port for internal services"""
    while True:
        port = random.randint(10240, 65295)
        import socket
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(('127.0.0.1', port))
            sock.close()
            return port
        except:
            continue

def main():
    print("=" * 60, flush=True)
    print("       CF Zero Trust Third Layer Protection", flush=True)
    print("   Additional Security Layer for Cloudflare Access", flush=True)
    print("=" * 60, flush=True)
    print("[CFTL] Layer 1: Cloudflare Access (Identity)", flush=True)
    print("[CFTL] Layer 2: Tunnel Configuration (Network)", flush=True)
    print("[CFTL] Layer 3: This System (Application)", flush=True)
    print("=" * 60, flush=True)
    
    # Register signal handlers for clean shutdown
    signal.signal(signal.SIGTERM, cleanup)
    signal.signal(signal.SIGINT, cleanup)
    
    # Basic configuration
    PORT = int(os.environ.get('PORT', '8080'))
    AUTH_PORT = find_free_port()
    os.environ['AUTH_PORT'] = str(AUTH_PORT)

    FALLBACK_PORT = find_free_port()
    while FALLBACK_PORT == AUTH_PORT:
        FALLBACK_PORT = find_free_port()
    os.environ['FALLBACK_PORT'] = str(FALLBACK_PORT)

    # Parse service configurations
    services = parse_services_env()
    
    if not services:
        print("\n[CFTL] WARNING: No services configured!", flush=True)
        print("[CFTL] Third layer protection is INACTIVE", flush=True)
        print("[CFTL] Configure CONFIGS environment variable to enable", flush=True)
        
        # Create default nginx config
        default_config = """
server {
    listen %d;
    server_name _;
    
    location / {
        return 200 'CF Zero Trust Third Layer\\nStatus: Not Configured\\n\\nSet CONFIGS environment variable to enable third layer protection\\n';
        add_header Content-Type text/plain;
    }
    
    location /health {
        return 200 'OK';
        add_header Content-Type text/plain;
    }
}
""" % PORT
        
        with open('/etc/nginx/sites-enabled/default.conf', 'w') as f:
            f.write(default_config)
    else:
        # Generate nginx configurations
        for i, service in enumerate(services):
            config = generate_nginx_config(service, PORT, AUTH_PORT)
            config_file = f'/etc/nginx/sites-enabled/service_{i}_{service.name}.conf'
            with open(config_file, 'w') as f:
                f.write(config)
        
        # Save authentication configurations
        save_auth_config(services)
    
    # Test nginx configuration
    result = subprocess.run(['nginx', '-t'], capture_output=True, text=True)
    if result.returncode != 0:
        print(f"[CFTL] ERROR: Nginx configuration test failed!", flush=True)
        print(result.stderr, flush=True)
        sys.exit(1)
    
    # Start third layer auth server
    auth_process = subprocess.Popen(
        ['python3', '/app/auth.py'],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(auth_process)
    time.sleep(2)

    # Start offline/fallback monitor
    offline_process = subprocess.Popen(
        ['python3', '/app/offline_fallback.py'],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(offline_process)
    time.sleep(2)
    
    # Start nginx
    nginx_process = subprocess.Popen(
        ['nginx', '-g', 'daemon off;'],
        stdout=sys.stdout,
        stderr=sys.stderr
    )
    processes.append(nginx_process)
    time.sleep(2)
    
    # Start Cloudflare tunnel if configured
    tunnel_token = os.environ.get('TUNNEL_TOKEN')
    tunnel_config = os.environ.get('TUNNEL_CONFIG')
    
    if tunnel_token:
        tunnel_process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--no-autoupdate', 'run', '--token', tunnel_token],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(tunnel_process)
    elif tunnel_config:
        with open('/tmp/tunnel.yml', 'w') as f:
            f.write(tunnel_config)
        
        tunnel_process = subprocess.Popen(
            ['cloudflared', 'tunnel', '--no-autoupdate', 'run', '--config', '/tmp/tunnel.yml'],
            stdout=sys.stdout,
            stderr=sys.stderr
        )
        processes.append(tunnel_process)
    else:
        print("\n[CFTL] WARNING: No TUNNEL_TOKEN or TUNNEL_CONFIG", flush=True)
        print("[CFTL] Running without Cloudflare tunnel (local only)", flush=True)
    
    print("\n" + "=" * 60, flush=True)
    print("[CFTL] All systems operational:", flush=True)
    print(f"  - Third Layer Auth: 127.0.0.1:{AUTH_PORT}", flush=True)
    print(f"  - Fallback Server: 127.0.0.1:{FALLBACK_PORT}", flush=True)
    print(f"  - Nginx Proxy: 0.0.0.0:{PORT}", flush=True)
    
    if services:
        print(f"\n[CFTL] Protected Services ({len(services)} total):", flush=True)
        
        with_auth = sum(1 for s in services if s.needs_auth())
        without_auth = len(services) - with_auth
        
        print(f"  - With third layer protection: {with_auth}", flush=True)
        print(f"  - Without third layer (bypass): {without_auth}", flush=True)
        
        print(f"\n[CFTL] Service Details:", flush=True)
        for service in services:
            if service.needs_auth():
                print(f"  ✓ {service.hostname} -> {service.service}:{service.port} [PROTECTED]", flush=True)
            else:
                print(f"  - {service.hostname} -> {service.service}:{service.port} [NO THIRD LAYER]", flush=True)
    
    if tunnel_token or tunnel_config:
        print(f"\n[CFTL] Cloudflare Tunnel: ACTIVE", flush=True)
        print(f"[CFTL] All three layers of Zero Trust are operational", flush=True)
    else:
        print(f"\n[CFTL] Cloudflare Tunnel: NOT CONFIGURED", flush=True)
        print(f"[CFTL] Only local access available", flush=True)
    
    print("=" * 60, flush=True)
    print("\n[CFTL] System ready. Press Ctrl+C to stop.", flush=True)
    
    # Monitor processes
    try:
        while True:
            for proc in processes:
                if proc.poll() is not None:
                    print(f"\n[CFTL] WARNING: A third layer process died!", flush=True)
                    cleanup()
            time.sleep(5)
    except KeyboardInterrupt:
        cleanup()

if __name__ == '__main__':
    main()

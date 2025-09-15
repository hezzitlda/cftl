#!/usr/bin/env python3
"""
Offline/fallback service manager for CFTL
Monitors services and switches between real backend and fallback
"""
import os
import socket
import subprocess
import time
import glob
import shutil
import re

ONLINE_CONFIGS = '/tmp/online_configs'
OFFLINE_CONFIGS = '/tmp/offline_configs'

def check_service_online(host: str, port: str) -> bool:
    """Check if a service is reachable"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((host, int(port)))
        sock.close()
        return result == 0
    except:
        return False

def prepare_configs():
    """Prepare online and offline versions of all configs"""
    fallback_port = os.environ.get('FALLBACK_PORT')
    services = []
    
    # Get all service configs (skip default.conf and fallback.conf)
    service_configs = glob.glob('/etc/nginx/sites-enabled/service_*.conf')
    
    for config_file in service_configs:
        filename = os.path.basename(config_file)
        
        with open(config_file, 'r') as f:
            content = f.read()
        
        # Extract host and port from first proxy_pass
        match = re.search(r'proxy_pass\s+http://([^:]+):(\d+)', content)
        if match:
            host = match.group(1)
            port = match.group(2)
            
            # Save service info
            services.append({
                'filename': filename,
                'host': host,
                'port': port,
                'online': True,
            })
            
            # Save online version (original)
            online_path = f'{ONLINE_CONFIGS}/{filename}'
            shutil.copy2(config_file, online_path)
            
            # Create and save offline version (with fallback)
            offline_content = re.sub(
                r'proxy_pass\s+http://[^:]+:\d+',
                f'proxy_pass http://127.0.0.1:{fallback_port}',
                content,
                count=1  # Only first occurrence
            )
            
            offline_path = f'{OFFLINE_CONFIGS}/{filename}'
            with open(offline_path, 'w') as f:
                f.write(offline_content)
    
    return services

def monitor_services(services):
    """Main monitoring loop"""
    while True:
        try:
            reload_needed = False
            
            for service in services:
                filename = service['filename']
                host = service['host']
                port = service['port']
                previous_state = service['online']
                
                nginx_path = f'/etc/nginx/sites-enabled/{filename}'
                current_state = check_service_online(host, port)
                
                if current_state:
                    service['online'] = True
                    source = f'{ONLINE_CONFIGS}/{filename}'
                else:
                    service['online'] = False
                    source = f'{OFFLINE_CONFIGS}/{filename}'
                
                # Only copy and print if state changed
                if previous_state != service['online']:
                    shutil.copy2(source, nginx_path)
                    reload_needed = True
                    
                    if service['online']:
                        print(f"[OFFLINE] {filename} switched to ONLINE", flush=True)
                    else:
                        print(f"[OFFLINE] {filename} switched to OFFLINE", flush=True)
            
            if reload_needed:
                subprocess.run(['nginx', '-s', 'reload'], capture_output=True)
            
            time.sleep(30)
                    
        except Exception as e:
            print(f"[OFFLINE] Monitor error: {e}", flush=True)
            time.sleep(30)

def main():
    """Main entry point"""
    os.makedirs(ONLINE_CONFIGS, exist_ok=True)
    os.makedirs(OFFLINE_CONFIGS, exist_ok=True)
    
    fallback_port = os.environ.get('FALLBACK_PORT')
    if not fallback_port:
        print("[OFFLINE] ERROR: FALLBACK_PORT environment variable not set", flush=True)
        return

    with open('/etc/nginx/sites-enabled/offline_fallback.conf', 'r+', encoding='utf-8') as file:
        content = file.read().replace('{FALLBACK_PORT}', fallback_port)
        file.seek(0)
        file.write(content)
        file.truncate()
    
    # Prepare configs and get service list
    services = prepare_configs()
    
    if not services:
        print("[OFFLINE] No services to monitor", flush=True)
        return
    
    # Start monitoring loop
    monitor_services(services)

if __name__ == '__main__':
    main()

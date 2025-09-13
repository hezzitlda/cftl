"""
CF Zero Trust Third Layer - Configuration Parser
"""

import os
import json
from typing import List, Dict, Optional

class ServiceConfig:
    """Service configuration for third layer protection"""
    
    def __init__(self, hostname: str, service: str, port: str, 
                 aud: Optional[str] = None, emails: Optional[List[str]] = None):
        self.hostname = hostname or '*'
        self.service = service
        self.port = port
        self.aud = aud
        self.emails = emails or []
        self.name = f"{hostname}_{service}".replace('.', '_').replace('*', 'default')
    
    def needs_auth(self) -> bool:
        """Check if this service requires third layer authentication"""
        return bool(self.aud)
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return {
            'hostname': self.hostname,
            'service': self.service,
            'port': self.port,
            'aud': self.aud,
            'emails': self.emails,
            'name': self.name
        }

def parse_services_env() -> List[ServiceConfig]:
    """Parse SERVICES environment variable """
    services = []
    services_env = os.environ.get('SERVICES', '')
    
    if not services_env:
        return services
    
    service_configs = services_env.split('|')
    
    for config_str in service_configs:
        config_str = config_str.strip()
        if not config_str:
            continue
        
        parts = config_str.split(':')
        
        if len(parts) < 3:
            print(f"[CFTL] ERROR: Invalid config (need hostname:service:port): {config_str}")
            continue
        
        hostname = parts[0].strip() or '*'
        service = parts[1].strip()
        port = parts[2].strip()
        
        aud = None
        if len(parts) > 3 and parts[3].strip():
            aud = parts[3].strip()
        
        emails = []
        if len(parts) > 4 and parts[4].strip():
            email_list = parts[4].strip().split(',')
            emails = [e.strip().lower() for e in email_list if e.strip()]
        
        config = ServiceConfig(hostname, service, port, aud, emails)
        services.append(config)
    
    return services

def generate_nginx_config(service: ServiceConfig, listen_port: int, auth_port: int) -> str:
    """Generate nginx configuration """
    if service.needs_auth():
        template_file = '/app/service-template.conf'
    else:
        template_file = '/app/service-noauth-template.conf'
    
    with open(template_file, 'r') as f:
        template = f.read()
    
    config = template.replace('{LISTEN_PORT}', str(listen_port))
    config = config.replace('{SERVER_NAME}', service.hostname if service.hostname != '*' else '_')
    config = config.replace('{SERVICE_HOST}', service.service)
    config = config.replace('{SERVICE_PORT}', service.port)
    config = config.replace('{SERVICE_NAME}', service.name)
    config = config.replace('{AUTH_PORT}', str(auth_port))
    
    return config

def save_auth_config(services: List[ServiceConfig]) -> None:
    """Save auth config """
    auth_configs = {}
    
    for service in services:
        if service.needs_auth():
            auth_configs[service.name] = {
                'hostname': service.hostname,
                'service': service.service,
                'aud': service.aud,
                'emails': service.emails
            }
    
    with open('/tmp/auth_config.json', 'w') as f:
        json.dump(auth_configs, f, indent=2)
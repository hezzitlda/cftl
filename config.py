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
        self.name = hostname.replace('.', '_').replace('*', 'default')
    
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
    """Parse new format configuration with aliases"""
    services = []
    
    auds = {}
    emails = {}
    hostnames = {}
    service_types = {}
    configs = []
    
    for key, value in os.environ.items():
        if key.startswith('AUDS'):
            for item in value.split('|'):
                if ':' in item:
                    alias, val = item.split(':', 1)
                    auds[alias.strip()] = val.strip()
                else:
                    auds['0'] = item.strip()
        
        elif key.startswith('EMAILS'):
            for item in value.split('|'):
                if ':' in item:
                    alias, val = item.split(':', 1)
                    emails[alias.strip()] = val.strip()
                else:
                    emails['0'] = item.strip()
        
        elif key.startswith('HOSTNAMES'):
            for item in value.split('|'):
                if ':' in item:
                    alias, val = item.split(':', 1)
                    hostnames[alias.strip()] = val.strip()
                else:
                    hostnames['0'] = item.strip()
        
        elif key.startswith('SERVICES'):
            for item in value.split('|'):
                if ':' in item:
                    alias, val = item.split(':', 1)
                    service_types[alias.strip()] = val.strip()
                else:
                    service_types['0'] = item.strip()
        
        elif key.startswith('CONFIGS'):
            configs.append(value.strip())
    
    for config_str in configs:
        if not config_str:
            continue
        
        parts = config_str.split(':')
        
        if len(parts) < 3:
            print(f"[CFTL] ERROR: Invalid config (need hostname_alias:service_alias:port[:aud_alias[:email_alias]]): {config_str}")
            continue
        
        hostname_alias = parts[0].strip()
        hostname = hostnames.get(hostname_alias, hostname_alias)
        
        service_alias = parts[1].strip()
        service = service_types.get(service_alias, service_alias)
        
        port = parts[2].strip()
        
        aud = None
        if len(parts) > 3 and parts[3].strip():
            aud_alias = parts[3].strip()
            aud = auds.get(aud_alias, aud_alias)
        
        email_list = []
        if len(parts) > 4 and parts[4].strip():
            email_alias = parts[4].strip()
            email_str = emails.get(email_alias, email_alias)
            email_list = [e.strip().lower() for e in email_str.split(',') if e.strip()]
        
        config = ServiceConfig(hostname, service, port, aud, email_list)
        services.append(config)
    
    return services

def generate_nginx_config(service: ServiceConfig, listen_port: int, auth_port: int) -> str:
    """Generate nginx configuration"""
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
    """Save auth config"""
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

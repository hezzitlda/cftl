<p align="center">
    <img src="https://raw.githubusercontent.com/hezzitlda/cftl/main/logo.png"
        height="100">
</p>

# 🛡️ CF Zero Trust Third Layer (CFTL)

**Additional Security Layer for Cloudflare Access Applications**

CFTL provides an extra validation layer on top of Cloudflare Zero Trust, adding application-level security with AUD validation and email-based access control.

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://hub.docker.com/r/hezzit/cftl)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](https://opensource.org/licenses/MIT)

## 🔐 Three Layers of Security

| Layer | Component              | Purpose                                        |
| ----- | ---------------------- | ---------------------------------------------- |
| **1** | **Cloudflare Access**  | Identity validation (SSO, MFA, policies)       |
| **2** | **Cloudflare Tunnel**  | Secure network connection + JWT validation     |
| **3** | **CFTL (This System)** | Additional AUD validation + email restrictions |

## 🚀 Quick Start

### Using Docker Image

```yaml
services:
  cftl:
    image: hezzit/cftl:latest
    container_name: cftl
    restart: always
    environment:
      - TUNNEL_TOKEN=your_tunnel_token_here #     v aud     v comma-separated list of emails
      - CONFIGS=your-app.example.com:my-app:3000:your_aud:your@email.com
        #			^ hostname		  ^ service:port				
    networks:
      - app-network
    depends_on:
      - app

  # Your application
  my-app:
    image: your-app:latest
    container_name: my-app
    networks:
      - app-network
    # No external ports - access only through CFTL

networks:
  app-network:
    external: false
```

## 🎯 Configuration System

CFTL uses a flexible alias-based configuration system that allows you to define reusable components and organize your services in multiple ways.

### Basic Structure

```bash
# Define reusable components with aliases
AUDS=aud_alias:aud_value
EMAILS=email_alias:email1@domain.com,email2@domain.com
HOSTNAMES=hostname_alias:hostname.example.com
SERVICES=service_alias:service_name

# Configure services using aliases
CONFIGS=hostname_alias:service_alias:port:aud_alias:email_alias
```

### Configuration Examples

#### Simple Configuration (Single Service)

```bash
# Define components
AUDS=prod:abc123def456789
EMAILS=team:admin@company.com,user@company.com
HOSTNAMES=app:myapp.example.com
SERVICES=backend:my-backend-service

# Configure the service
CONFIGS=app:backend:3000:prod:team
```

#### Multiple Services

```bash
# Define shared components
AUDS=prod:abc123def456789
EMAILS=admin:admin@company.com|dev:dev@company.com
HOSTNAMES=api:api.example.com|web:web.example.com
SERVICES=backend:backend-api|frontend:nginx

# Configure each service
CONFIGS_API=api:backend:3000:prod:admin
CONFIGS_WEB=web:frontend:80:prod:dev
```

#### Advanced Organization Patterns

##### Pattern 1: Environment-Based

```bash
# Development environment
AUDS_DEV=dev:dev_aud_123
EMAILS_DEV=devteam:dev1@company.com,dev2@company.com
HOSTNAMES_DEV=ide:ide.dev.example.com|debug:debug.dev.example.com
SERVICES_DEV=vscode:code-server
CONFIGS_DEV_IDE=ide:vscode:8080:dev:devteam
CONFIGS_DEV_DEBUG=debug:vscode:8081:dev:devteam

# Production environment
AUDS_PROD=prod:prod_aud_456
EMAILS_PROD=ops:ops@company.com
HOSTNAMES_PROD=app:app.example.com|api:api.example.com
SERVICES_PROD=web:nginx|api:backend
CONFIGS_PROD_APP=app:web:80:prod:ops
CONFIGS_PROD_API=api:api:3000:prod:ops
```

##### Pattern 2: Team-Based

```bash
# Frontend team resources
AUDS_FRONTEND=fe:frontend_aud
EMAILS_FRONTEND=fe_team:frontend@company.com
HOSTNAMES_FRONTEND=app:app.example.com|preview:preview.example.com

# Backend team resources
AUDS_BACKEND=be:backend_aud
EMAILS_BACKEND=be_team:backend@company.com
HOSTNAMES_BACKEND=api:api.example.com|admin:admin.example.com

# Shared services
SERVICES=nginx:nginx|node:nodejs|python:python-app

# Service configurations
CONFIGS_FE_APP=app:nginx:80:fe:fe_team
CONFIGS_FE_PREVIEW=preview:node:3000:fe:fe_team
CONFIGS_BE_API=api:python:8000:be:be_team
CONFIGS_BE_ADMIN=admin:node:4000:be:be_team
```

##### Pattern 3: Simplified (Using Defaults)

```bash
# When you don't need aliases, values without ':' use '0' as default alias
AUDS=abc123def456789
EMAILS=admin@company.com,user@company.com
HOSTNAMES=app.example.com
SERVICES=backend

# Reference using '0' alias
CONFIGS=0:0:3000:0:0
```

### Special Cases

#### Service Without Authentication

```bash
# Empty AUD and emails fields = no third layer protection
CONFIGS_PUBLIC=public:nginx:80::
```

#### Only AUD Validation (No Email Restriction)

```bash
CONFIGS_API=api:backend:3000:prod:
#                                   ^ no email restriction
```

#### Mixed Configuration Styles

```bash
# You can mix all patterns in one deployment
AUDS=prod:prod_aud|staging:staging_aud
EMAILS=admin@company.com  # Uses '0' as default alias
HOSTNAMES_PROD=app:app.example.com
HOSTNAMES_DEV=dev:dev.example.com
SERVICES=backend:my-backend|frontend:nginx

# Multiple CONFIGS variations
CONFIGS=app:backend:3000:prod:0|dev:frontend:80:staging:0  # Using default email alias
CONFIGS_PUBLIC=public.example.com:nginx:80::  # Direct values without aliases
```

## 📋 Complete Setup Guide

### Step 1: Configure Authentication Method

First, set up your identity provider integration:

📖 **Guide**: [Identity Provider Integration](https://developers.cloudflare.com/cloudflare-one/identity/idp-integration/)

**Popular options:**
- GitHub OAuth
- Google
- Azure AD
- Generic OIDC

### Step 2: Create Access Policies

Define who can access your applications:

📖 **Guide**: [Access Policies](https://developers.cloudflare.com/cloudflare-one/policies/access/)

**Example policy:**
- **Policy Name**: "Admin Access"
- **Rule**: Email contains `admin@yourcompany.com`
- **Action**: Allow

### Step 3: Create Access Application

Set up your application in Cloudflare Access:

📖 **Guide**: [Self-Hosted Applications](https://developers.cloudflare.com/cloudflare-one/applications/configure-apps/self-hosted-public-app/)

**Configuration:**
1. **Application Name**: Your App Name
2. **Application Domain**: `your-app.example.com`
3. **Authentication Method**: Select your configured method (GitHub, Google, etc.)
4. **Policies**: Select your access policy
5. **Save and copy the Application AUD** (you'll need this later)

### Step 4: Create Cloudflare Tunnel

Set up secure connection to your application:

📖 **Guide**: [Create Remote Tunnel](https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-remote-tunnel/)

**Configuration:**
1. **Tunnel Name**: Your tunnel name
2. **Public Hostname**: `your-app.example.com` (same as Access app)
3. **Service**: `http://localhost:8080` (CFTL proxy port)

**⚠️ IMPORTANT - Additional Settings:**
- Navigate to **Access** tab in tunnel configuration
- **Enable "Validate JWT"**
- **Select your Access Application** (created in Step 3)

4. **Save and copy the Tunnel Token**

### Step 5: Configure CFTL

Choose your configuration style:

#### Option A: Simple Configuration
```bash
CONFIGS=your-app.example.com:your-service:3000:your_aud_from_step_3:authorized@email.com
```

#### Option B: Multi-Service Configuration
```bash
TUNNEL_TOKEN=your_tunnel_token

# Define all your AUDs
AUDS=prod:aud_123|staging:aud_456

# Define email groups
EMAILS=admin:admin@company.com|dev:dev@company.com,dev2@company.com

# Define all hostnames
HOSTNAMES=app:app.example.com|api:api.example.com|admin:admin.example.com

# Define service types
SERVICES=web:nginx|backend:nodejs-api

# Configure each service
CONFIGS_APP=app:web:80:prod:admin
CONFIGS_API=api:backend:3000:prod:dev
CONFIGS_ADMIN=admin:backend:4000:staging:admin
```

### Step 6: Deploy

```bash
docker-compose up -d
```

## 🔧 Environment Variables

### Core Variables

| Variable       | Description             | Required | Example                               |
| -------------- | ----------------------- | -------- | ------------------------------------- |
| `TUNNEL_TOKEN` | Cloudflare Tunnel token | ✅       | `eyJhbGci...`                         |
| `PORT`   | CFTL listening port    | ❌       | `8080` (default)                      |
| `VERBOSE`      | Enable verbose logging  | ❌       | `false` (default)                     |

### Configuration Variables

| Variable Pattern | Description | Example |
|-----------------|-------------|---------|
| `AUDS*` | AUD definitions | `AUDS=prod:abc123` or `AUDS_DEV=dev:xyz789` |
| `EMAILS*` | Email group definitions | `EMAILS=admin:admin@company.com` |
| `HOSTNAMES*` | Hostname definitions | `HOSTNAMES=app:app.example.com` |
| `SERVICES*` | Service type definitions | `SERVICES=backend:my-backend` |
| `CONFIGS*` | Service configurations | `CONFIGS_APP=app:backend:3000:prod:admin` |

*Note: All patterns support multiple definitions (AUDS, AUDS_1, AUDS_PROD, etc.)*

## 🔍 How It Works

1. **User visits** `your-app.example.com`
2. **Cloudflare Access** validates identity (Layer 1)
3. **Cloudflare Tunnel** validates JWT and forwards to CFTL (Layer 2)
4. **CFTL** validates AUD and email authorization (Layer 3)
5. **If all layers pass**, request is forwarded to your application

### User Headers Passed to Application

When authentication is successful, your application receives these HTTP headers:

| Header | Description | Example |
|--------|-------------|---------|
| `X-Auth-User-Email` | User's email address | `user@company.com` |
| `X-Auth-User-ID` | Unique user ID (CF Access sub) | `7335d417-61da-459d-899c-0a01c76a2f94` |
| `X-Auth-User-Country` | User's authentication country | `US` |
| `X-Auth-Method` | Authentication method used | `cf-access-third-layer` |
| `X-Auth-Service` | Service name (internal) | `app_example_com` |
| `X-Auth-AUD` | Validated CF Access AUD | `abc123def456...` |
| `X-Auth-Issuer` | CF Access issuer URL | `https://yourteam.cloudflareaccess.com` |
| `X-Auth-Token-Type` | Token type | `app` |
| `X-Auth-Identity-Nonce` | CF identity cache key | `6ei69kawdKzMIAPF` |

### Using Headers in Your Application

**Flask (Python):**
```python
@app.route('/')
def index():
    user_email = request.headers.get('X-Auth-User-Email')
    user_country = request.headers.get('X-Auth-User-Country')
    return f"Welcome {user_email} from {user_country}"
```

**Express.js (Node.js):**
```javascript
app.get('/', (req, res) => {
    const userEmail = req.headers['x-auth-user-email'];
    const userCountry = req.headers['x-auth-user-country'];
    res.send(`Welcome ${userEmail} from ${userCountry}`);
});
```

**Note:** Only services **with third layer protection** receive user headers. Services without third layer (bypass mode) are direct proxied without authentication headers.

## 🛠️ Troubleshooting

### Check System Status

```bash
docker-compose logs cftl
```

### Common Issues

| Issue | Possible Cause | Solution |
|-------|---------------|----------|
| `DENIED: No CF Access token` | Domain mismatch between Access App and CFTL | Ensure Access Application domain matches CFTL hostname exactly |
| `DENIED: AUD mismatch` | Wrong AUD in configuration | Copy correct AUD from Access Application |
| `DENIED: Unauthorized email` | Email not in authorized list | Add email to EMAILS configuration |
| Nginx error page (white/plain) | Issue between CFTL and your app | Check app connectivity and port configuration |
| Browser error (empty response/connection reset) | Issue between Tunnel and Access App | Ensure tunnel hostname matches Access Application domain exactly |
| Tunnel not connecting | Invalid tunnel token | Generate new token from tunnel settings |

### Test Individual Layers

```bash
# Test if tunnel is working
curl -I https://your-app.example.com

# Check CFTL logs for third layer validation
docker-compose logs -f cftl
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](https://raw.githubusercontent.com/hezzitlda/cftl/main/LICENSE) file for details.

---

Built with ❤️ by Hezzit. Contributions are welcome!

**⭐ If this project helped you, please give it a star!**

<p align="center">
    <img src="https://raw.githubusercontent.com/hezzitlda/cftl/main/logo.png"
        height="100">
</p>

# 🛡️ CF Zero Trust Third Layer (CFTL)

**Additional Security Layer for Cloudflare Access Applications**

CFTL provides an extra validation layer on top of Cloudflare Zero Trust, adding application-level security with AUD validation and email-based access control.

[![Docker](https://img.shields.io/badge/docker-%230db7ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://github.com/users/hezzitlda/packages/container/package/cftl)
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
    image: ghcr.io/hezzitlda/cftl:latest
    container_name: cftl
    restart: always
    environment:
      - TUNNEL_TOKEN=your_tunnel_token_here
      - SERVICES=your-app.example.com:app:3000:your_cf_access_aud:admin@example.com
    networks:
      - app-network
    depends_on:
      - app

  # Your application
  app:
    image: your-app:latest
    container_name: app
    networks:
      - app-network
    # No external ports - access only through CFTL

networks:
  app-network:
    external: false
```

### Configuration Format

```bash
SERVICES=hostname:service:port:aud:emails

# Examples:
# Without third layer: app.example.com:backend:3000::
# With AUD only: app.example.com:backend:3000:your_aud:
# With AUD + emails: app.example.com:backend:3000:your_aud:admin@company.com,user@company.com
# Multiple services: app1.example.com:svc1:3000:aud1:admin@company.com|app2.example.com:svc2:4000:aud2:
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

Create your configuration:

```bash
# Required
TUNNEL_TOKEN=your_tunnel_token_from_step_4
SERVICES=your-app.example.com:your-service:port:your_aud_from_step_3:authorized@emails.com

# Optional
NGINX_PORT=8080
VERBOSE=false
```

### Step 6: Deploy

```bash
docker-compose up -d
```

## 🔧 Environment Variables

| Variable       | Description             | Required | Example                               |
| -------------- | ----------------------- | -------- | ------------------------------------- |
| `TUNNEL_TOKEN` | Cloudflare Tunnel token | ✅       | `eyJhbGci...`                         |
| `SERVICES`     | Service configuration   | ✅       | `app.com:svc:3000:aud:user@email.com` |
| `NGINX_PORT`   | Nginx listening port    | ❌       | `8080` (default)                      |
| `VERBOSE`      | Enable verbose logging  | ❌       | `false` (default)                     |

## 📊 Service Configuration Examples

### Single Protected Service

```bash
SERVICES=secure.example.com:backend:3000:abc123def456:admin@company.com,user@company.com
```

### Multiple Services (Mixed Protection)

```bash
SERVICES=secure.example.com:backend:3000:abc123:admin@company.com|public.example.com:nginx:80::
```

### Service Without Third Layer (Direct Proxy)

```bash
SERVICES=public.example.com:static:80::
```

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
| `X-Auth-Service` | Service name (internal) | `app_example_com_backend` |
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

| Issue                                           | Possible Cause                              | Solution                                                         |
| ----------------------------------------------- | ------------------------------------------- | ---------------------------------------------------------------- |
| `DENIED: No CF Access token`                    | Domain mismatch between Access App and CFTL | Ensure Access Application domain matches CFTL hostname exactly   |
| `DENIED: AUD mismatch`                          | Wrong AUD in configuration                  | Copy correct AUD from Access Application                         |
| `DENIED: Unauthorized email`                    | Email not in authorized list                | Add email to SERVICES configuration                              |
| Nginx error page (white/plain)                  | Issue between CFTL and your app             | Check app connectivity and port configuration                    |
| Browser error (empty response/connection reset) | Issue between Tunnel and Access App         | Ensure tunnel hostname matches Access Application domain exactly |
| Tunnel not connecting                           | Invalid tunnel token                        | Generate new token from tunnel settings                          |

### Test Individual Layers

```bash
# Test if tunnel is working
curl -I https://your-app.example.com

# Check CFTL logs for third layer validation
docker-compose logs -f cftl
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

Built with ❤️ by Hezzit. Contributions are welcome!

**⭐ If this project helped you, please give it a star!**

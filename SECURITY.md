# Security Policy

## Supported Versions

| Version | Supported          |
| ------- | ------------------ |
| latest  | :white_check_mark: |

## Reporting a Vulnerability

We take security seriously. If you discover a security vulnerability, please follow these steps:

### 1. Do NOT Create a Public Issue

Please do not report security vulnerabilities through public GitHub issues.

### 2. Report Privately

Send an email to the repository maintainer with:

- A description of the vulnerability
- Steps to reproduce the issue
- Potential impact assessment
- Any suggested fixes (optional)

### 3. What to Expect

- **Acknowledgment**: We will acknowledge receipt within 48 hours
- **Assessment**: We will assess the vulnerability and determine its severity
- **Fix Timeline**: Critical issues will be addressed as soon as possible
- **Disclosure**: We will coordinate with you on public disclosure timing

## Security Best Practices for Self-Hosting

When deploying FinanceAICrews, please follow these security guidelines:

### Environment Variables

```bash
# Generate strong secrets
JWT_SECRET_KEY=$(openssl rand -base64 32)
ENCRYPTION_KEY=$(python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())")
```

### Database

- Use strong passwords for PostgreSQL
- Restrict database access to localhost or trusted networks
- Enable SSL for database connections in production

### API Keys

- Never commit API keys to version control
- Use environment variables or secure secret management
- Rotate keys periodically
- Use the BYOK (Bring Your Own Key) feature for user-provided keys

### Network Security

- Use HTTPS in production (reverse proxy with nginx/caddy)
- Configure proper CORS settings
- Use firewall rules to restrict access

### Docker Security

- Don't run containers as root
- Use read-only file systems where possible
- Keep images updated

## Known Security Considerations

### LLM A Keys

- User API keys (BYOK) are encrypted at rest using Fernet encryption
- The `ENCRYPTION_KEY` environment variable must be kept secure
- Keys are never logged or exposed in error messages

### Authentication

- JWT tokens are used for authentication
- Tokens expire after a configurable period
- Refresh token rotation is implemented

### Data Privacy

- Financial analysis results are stored per-user
- No data is shared between users
- Self-hosted deployments keep all data local

## Security Updates

Watch this repository for security-related releases and updates.

---

Thank you for helping keep FinanceAICrews secure!

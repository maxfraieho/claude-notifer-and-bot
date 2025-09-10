# 🔒 Security Guide for Claude Telegram Bot

## Critical Security Considerations

### 1. Claude CLI Authentication (`~/.claude`)

**CRITICAL**: The `~/.claude` directory contains authentication tokens for Claude CLI.

#### Security Best Practices:
```bash
# Set proper permissions (read-only for owner only)
chmod 700 ~/.claude
chmod 600 ~/.claude/*

# Verify permissions
ls -la ~/.claude
# Should show: drwx------ (700) for directory
# Should show: -rw------- (600) for files
```

#### Container Security:
```yaml
# In docker-compose.remote.yml - mount as read-only
volumes:
  - ~/.claude:/home/claudebot/.claude:ro  # ✅ Read-only mount
```

#### Backup Security:
```bash
# Secure backup of authentication
tar -czf claude-auth-backup.tar.gz ~/.claude/
chmod 600 claude-auth-backup.tar.gz

# Store in secure location (encrypted storage recommended)
```

### 2. Volume Mounting Security

#### Secure Volume Configuration:
```yaml
volumes:
  # ✅ Data directory - read/write needed
  - ./data:/app/data

  # ✅ Target project - read/write for file operations
  - ./target_project:/app/target_project

  # ✅ Claude auth - read-only for security
  - ~/.claude:/home/claudebot/.claude:ro
  
  # ❌ NEVER mount entire filesystem
  # - /:/host  # DANGEROUS!
  
  # ❌ NEVER mount sensitive directories unless needed
  # - /etc:/host/etc
  # - /var:/host/var
```

#### Directory Permissions:
```bash
# Set secure permissions for mounted directories
chmod 755 ./data ./target_project
chown 1001:1001 ./data ./target_project  # Match container user

# Verify no sensitive files in target_project
find ./target_project -name "*.key" -o -name "*.pem" -o -name "*secret*"
```

### 3. Environment Variables Security

#### Production .env Security:
```bash
# Set secure permissions for .env file
chmod 600 .env
chown root:root .env  # Or your user

# ✅ Required production variables
TELEGRAM_BOT_TOKEN=bot123456:SECURE_TOKEN_HERE
ALLOWED_USERS=123456789,987654321  # ALWAYS set in production

# ✅ Optional but recommended
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secure_random_string_here

# ❌ NEVER commit .env to git
echo ".env" >> .gitignore
```

#### Environment Variable Validation:
```bash
# Check for empty or default values
grep -E "^[A-Z_]+=(\s*|test|demo|example)" .env && echo "⚠️  Found default/empty values"

# Check for hardcoded development values
grep -E "(localhost|127.0.0.1|dev|debug=true)" .env && echo "⚠️  Found development values"
```

### 4. Container Security

#### User Security:
```dockerfile
# ✅ Run as non-root user
USER 1001:1001

# ✅ Set in docker-compose
user: "1001:1001"
```

#### Resource Limits:
```yaml
# ✅ Prevent resource exhaustion attacks
deploy:
  resources:
    limits:
      memory: 1G
      cpus: '1.0'
```

#### Network Security:
```yaml
# ✅ Don't expose unnecessary ports
# ports: []  # No ports if not using webhooks

# ✅ Use custom network if needed
networks:
  claude_network:
    driver: bridge
```

### 5. Telegram Bot Security

#### Bot Token Security:
```bash
# ✅ Strong bot token from @BotFather
TELEGRAM_BOT_TOKEN=1234567890:ABCDEFghijklmnopQRSTUVwxyz123456789

# ✅ Set bot privacy mode
# In @BotFather: /setprivacy -> Enable -> Your bot can only see messages sent to it

# ✅ Configure allowed users (MANDATORY for production)
ALLOWED_USERS=123456789,987654321
```

#### Access Control:
```bash
# Check your Telegram user ID
# Send any message to @userinfobot to get your ID

# ✅ Whitelist approach - only specific users
ALLOWED_USERS=123456789,987654321

# ✅ Optional token-based auth for additional security
ENABLE_TOKEN_AUTH=true
AUTH_TOKEN_SECRET=your_secure_random_32_char_string
```

### 6. File System Security

#### Directory Isolation:
```bash
# ✅ Create isolated directory structure
mkdir -p ~/claude-bot-prod/{data,target_project,logs}
cd ~/claude-bot-prod

# ✅ Set proper ownership and permissions
chown -R 1001:1001 data/ target_project/
chmod 755 data/ target_project/

# ❌ NEVER run bot with root privileges
# ❌ NEVER mount system directories unnecessarily
```

#### File Permission Monitoring:
```bash
# Monitor for permission changes
find ./data ./target_project -type f \( -perm -002 -o -perm -020 \) -ls
# Should return no world/group writable files
```

### 7. Network Security

#### Firewall Configuration:
```bash
# ✅ Configure UFW (Ubuntu) or iptables
sudo ufw default deny incoming
sudo ufw default allow outgoing
sudo ufw allow ssh
# Only add ports if using webhook mode:
# sudo ufw allow 8443/tcp
sudo ufw enable
```

#### Docker Network Security:
```bash
# ✅ Check Docker network configuration
docker network ls
docker network inspect bridge

# ✅ Consider custom network for isolation
docker network create claude_network --driver bridge --subnet=172.21.0.0/16
```

### 8. Logging and Monitoring Security

#### Secure Logging:
```yaml
# ✅ Limit log file sizes to prevent disk exhaustion
logging:
  driver: "json-file"
  options:
    max-size: "50m"
    max-file: "5"
```

#### Log Security:
```bash
# ✅ Set proper permissions on log files
chmod 640 /var/lib/docker/containers/*/hostconfig.json
chown root:docker /var/lib/docker/containers/*/hostconfig.json

# ✅ Regular log rotation
sudo logrotate -f /etc/logrotate.d/docker
```

### 9. Backup Security

#### Secure Backup Strategy:
```bash
#!/bin/bash
# secure-backup.sh

BACKUP_DIR="/var/backups/claude-bot"
DATE=$(date +%Y%m%d-%H%M)
BACKUP_FILE="$BACKUP_DIR/claude-bot-$DATE.tar.gz"

# Create backup with encryption
tar -czf - data/ target_project/ ~/.claude/ .env | \
  gpg --cipher-algo AES256 --compress-algo 1 --symmetric \
      --output "$BACKUP_FILE.gpg"

# Set secure permissions
chmod 600 "$BACKUP_FILE.gpg"

# Remove unencrypted temporary files
find /tmp -name "*claude*" -type f -mmin +60 -delete
```

#### Backup Verification:
```bash
# Test backup integrity
gpg --decrypt "$BACKUP_FILE.gpg" | tar -tzf - > /dev/null
echo "Backup integrity: $?"
```

### 10. Update Security

#### Secure Update Process:
```bash
#!/bin/bash
# secure-update.sh

# 1. Verify image signature (if available)
docker trust inspect kroschu/claude-notifer-chat-amd64:latest

# 2. Pull with verification
docker pull kroschu/claude-notifer-chat-amd64:latest

# 3. Stop current container
docker-compose -f docker-compose.remote.yml stop

# 4. Create backup before update
./secure-backup.sh

# 5. Start with new image
docker-compose -f docker-compose.remote.yml up -d

# 6. Verify deployment
sleep 30
docker-compose -f docker-compose.remote.yml ps
docker-compose -f docker-compose.remote.yml logs --tail=20
```

## Security Checklist

### Pre-Deployment:
- [ ] `.env` file has production values (no defaults)
- [ ] `ALLOWED_USERS` is set with your Telegram ID
- [ ] Claude CLI authentication is working
- [ ] `~/.claude` directory has correct permissions (700)
- [ ] Container runs as non-root user (1001:1001)
- [ ] No sensitive files in `target_project` directory

### Post-Deployment:
- [ ] Bot responds only to authorized users
- [ ] Container health checks are passing
- [ ] Logs show no permission errors
- [ ] No exposed ports unless needed for webhooks
- [ ] Backup strategy is implemented
- [ ] Monitoring is configured

### Regular Security Maintenance:
- [ ] Update base images regularly
- [ ] Rotate Telegram bot tokens periodically
- [ ] Review and rotate Claude CLI authentication
- [ ] Monitor for unusual activity in logs
- [ ] Test backup and restore procedures
- [ ] Keep Docker and system updated

## Incident Response

### If Bot Token is Compromised:
1. Revoke token immediately in @BotFather
2. Create new bot token
3. Update `.env` file
4. Restart container
5. Monitor for unauthorized usage

### If Claude Authentication is Compromised:
1. Logout from Claude CLI: `claude auth logout`
2. Re-authenticate: `claude auth login`
3. Verify new authentication: `claude auth status`
4. Restart container
5. Check for unauthorized Claude usage

### If Server is Compromised:
1. Stop all containers immediately
2. Isolate server from network
3. Create forensic backup
4. Analyze logs for attack vectors
5. Rebuild server from clean state
6. Restore data from secure backups
7. Implement additional security measures

## Emergency Contacts

- Anthropic Security: security@anthropic.com
- Telegram Security: security@telegram.org
- Your Infrastructure Team: [your-contact-info]

## Regular Security Reviews

Schedule monthly reviews of:
- Access logs
- User permissions
- Container security updates
- Backup integrity tests
- Network configuration changes
- Authentication token rotation
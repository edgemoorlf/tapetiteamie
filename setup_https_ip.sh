#!/bin/bash

# Automated HTTPS Setup for IP-Only (No Domain Name)
# This script sets up Nginx with self-signed SSL certificate

set -e  # Exit on error

echo "=========================================="
echo "HTTPS Setup for IP-Only Configuration"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    echo "❌ Please run as root (use sudo)"
    exit 1
fi

# Get public IP
echo "🔍 Detecting public IP address..."
PUBLIC_IP=$(curl -s ifconfig.me || curl -s icanhazip.com || curl -s ipinfo.io/ip)

if [ -z "$PUBLIC_IP" ]; then
    echo "❌ Could not detect public IP automatically"
    read -p "Please enter your public IP address: " PUBLIC_IP
fi

echo "✅ Public IP: $PUBLIC_IP"
echo ""

# Confirm with user
read -p "Is this correct? (y/n): " confirm
if [ "$confirm" != "y" ]; then
    read -p "Enter your public IP address: " PUBLIC_IP
fi

echo ""
echo "=========================================="
echo "Step 1: Removing iptables redirect"
echo "=========================================="

# Check if iptables redirect exists
if iptables -t nat -L PREROUTING -n | grep -q "REDIRECT.*tcp dpt:80 redir ports 5000"; then
    echo "Found iptables redirect, removing..."
    iptables -t nat -D PREROUTING -p tcp --dport 80 -j REDIRECT --to-port 5000

    # Save iptables rules
    if command -v iptables-save &> /dev/null; then
        iptables-save > /etc/iptables/rules.v4 2>/dev/null || true
    fi

    echo "✅ iptables redirect removed"
else
    echo "ℹ️  No iptables redirect found (skipping)"
fi

echo ""
echo "=========================================="
echo "Step 2: Installing Nginx"
echo "=========================================="

if command -v nginx &> /dev/null; then
    echo "ℹ️  Nginx already installed"
else
    echo "Installing Nginx..."
    apt-get update
    apt-get install -y nginx
    echo "✅ Nginx installed"
fi

echo ""
echo "=========================================="
echo "Step 3: Generating SSL certificate"
echo "=========================================="

# Create directories if they don't exist
mkdir -p /etc/ssl/private
mkdir -p /etc/ssl/certs

# Generate self-signed certificate
echo "Generating self-signed certificate for $PUBLIC_IP..."
openssl req -x509 -nodes -days 365 -newkey rsa:2048 \
  -keyout /etc/ssl/private/voice-video.key \
  -out /etc/ssl/certs/voice-video.crt \
  -subj "/C=US/ST=State/L=City/O=VoiceVideo/CN=$PUBLIC_IP"

# Set proper permissions
chmod 600 /etc/ssl/private/voice-video.key
chmod 644 /etc/ssl/certs/voice-video.crt

echo "✅ SSL certificate generated"
echo "   Certificate: /etc/ssl/certs/voice-video.crt"
echo "   Private key: /etc/ssl/private/voice-video.key"

echo ""
echo "=========================================="
echo "Step 4: Configuring Nginx"
echo "=========================================="

# Create Nginx configuration
cat > /etc/nginx/sites-available/voice-video << EOF
# HTTP server - redirects to HTTPS
server {
    listen 80;
    server_name $PUBLIC_IP;
    return 301 https://\$server_name\$request_uri;
}

# HTTPS server - main application
server {
    listen 443 ssl http2;
    server_name $PUBLIC_IP;

    # Self-signed SSL certificate
    ssl_certificate /etc/ssl/certs/voice-video.crt;
    ssl_certificate_key /etc/ssl/private/voice-video.key;

    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_ciphers HIGH:!aNULL:!MD5;
    ssl_prefer_server_ciphers on;

    location / {
        proxy_pass http://localhost:5000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;

        # WebSocket support
        proxy_read_timeout 86400;
        proxy_buffering off;
    }
}
EOF

echo "✅ Nginx configuration created"

# Enable the site
if [ -f /etc/nginx/sites-enabled/voice-video ]; then
    echo "ℹ️  Site already enabled"
else
    ln -s /etc/nginx/sites-available/voice-video /etc/nginx/sites-enabled/
    echo "✅ Site enabled"
fi

# Remove default site if it exists
if [ -f /etc/nginx/sites-enabled/default ]; then
    rm /etc/nginx/sites-enabled/default
    echo "✅ Default site removed"
fi

# Test Nginx configuration
echo ""
echo "Testing Nginx configuration..."
if nginx -t; then
    echo "✅ Nginx configuration valid"
else
    echo "❌ Nginx configuration invalid"
    exit 1
fi

echo ""
echo "=========================================="
echo "Step 5: Configuring firewall"
echo "=========================================="

if command -v ufw &> /dev/null; then
    echo "Configuring UFW firewall..."

    # Allow ports
    ufw allow 22/tcp comment 'SSH'
    ufw allow 80/tcp comment 'HTTP'
    ufw allow 443/tcp comment 'HTTPS'

    # Enable firewall (if not already enabled)
    ufw --force enable

    echo "✅ Firewall configured"
    echo ""
    ufw status
else
    echo "⚠️  UFW not installed, skipping firewall configuration"
    echo "   Make sure ports 80 and 443 are open in your firewall"
fi

echo ""
echo "=========================================="
echo "Step 6: Starting Nginx"
echo "=========================================="

# Restart Nginx
systemctl restart nginx

# Check status
if systemctl is-active --quiet nginx; then
    echo "✅ Nginx is running"
else
    echo "❌ Nginx failed to start"
    systemctl status nginx
    exit 1
fi

echo ""
echo "=========================================="
echo "✅ Setup Complete!"
echo "=========================================="
echo ""
echo "Next steps:"
echo ""
echo "1. Start your Flask application:"
echo "   cd /Users/liangfang/codes/tapetiteamie"
echo "   python server.py"
echo ""
echo "2. Access your application:"
echo "   https://$PUBLIC_IP"
echo ""
echo "⚠️  IMPORTANT: Browser Security Warning"
echo "   You will see a security warning because of the self-signed certificate."
echo "   This is NORMAL and EXPECTED."
echo ""
echo "   To bypass the warning:"
echo "   - Chrome/Edge: Click 'Advanced' → 'Proceed to $PUBLIC_IP (unsafe)'"
echo "   - Firefox: Click 'Advanced' → 'Accept the Risk and Continue'"
echo "   - Safari: Click 'Show Details' → 'visit this website'"
echo ""
echo "   After bypassing the warning, the microphone will work! ✅"
echo ""
echo "=========================================="
echo "Verification Commands:"
echo "=========================================="
echo ""
echo "# Check if all services are running"
echo "sudo netstat -tlnp | grep -E ':(80|443|5000)'"
echo ""
echo "# Test HTTP redirect"
echo "curl -I http://$PUBLIC_IP"
echo ""
echo "# Test HTTPS connection (ignore cert validation)"
echo "curl -k -I https://$PUBLIC_IP"
echo ""
echo "# View Nginx logs"
echo "sudo tail -f /var/log/nginx/error.log"
echo ""
echo "=========================================="

#!/bin/bash

# SSL Certificate Setup Script
# This script helps you set up SSL certificates for HTTPS support

echo "=========================================="
echo "SSL Certificate Setup"
echo "=========================================="
echo ""

# Check if openssl is installed
if ! command -v openssl &> /dev/null; then
    echo "❌ Error: openssl is not installed"
    echo "   Install it with: sudo apt-get install openssl"
    exit 1
fi

echo "Choose an option:"
echo "1) Generate self-signed certificate (for testing)"
echo "2) Use Let's Encrypt certificate (for production)"
echo "3) Use existing certificate files"
echo ""
read -p "Enter your choice (1-3): " choice

case $choice in
    1)
        echo ""
        echo "Generating self-signed certificate..."
        echo ""

        # Generate self-signed certificate
        openssl req -x509 -newkey rsa:4096 -nodes \
            -out cert.pem \
            -keyout key.pem \
            -days 365 \
            -subj "/C=CN/ST=State/L=City/O=Organization/CN=localhost"

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Certificate generated successfully!"
            echo "   Certificate: cert.pem"
            echo "   Private key: key.pem"
            echo ""
            echo "⚠️  Note: Self-signed certificates will show a security warning in browsers."
            echo "   This is normal for testing. Click 'Advanced' and 'Proceed' to continue."
        else
            echo "❌ Failed to generate certificate"
            exit 1
        fi
        ;;

    2)
        echo ""
        echo "Setting up Let's Encrypt certificate..."
        echo ""

        # Check if certbot is installed
        if ! command -v certbot &> /dev/null; then
            echo "❌ Error: certbot is not installed"
            echo "   Install it with:"
            echo "   sudo apt-get update"
            echo "   sudo apt-get install certbot"
            exit 1
        fi

        read -p "Enter your domain name: " domain

        echo ""
        echo "Running certbot..."
        echo "Note: Make sure port 80 is open and your domain points to this server"
        echo ""

        sudo certbot certonly --standalone -d "$domain"

        if [ $? -eq 0 ]; then
            echo ""
            echo "✅ Certificate obtained successfully!"
            echo ""
            echo "Add these lines to your .env file:"
            echo "USE_SSL=true"
            echo "SSL_CERT_PATH=/etc/letsencrypt/live/$domain/fullchain.pem"
            echo "SSL_KEY_PATH=/etc/letsencrypt/live/$domain/privkey.pem"
            echo ""
            echo "⚠️  Note: You may need to run the server with sudo to access these files"
        else
            echo "❌ Failed to obtain certificate"
            exit 1
        fi
        ;;

    3)
        echo ""
        read -p "Enter path to certificate file: " cert_path
        read -p "Enter path to private key file: " key_path

        if [ ! -f "$cert_path" ]; then
            echo "❌ Error: Certificate file not found: $cert_path"
            exit 1
        fi

        if [ ! -f "$key_path" ]; then
            echo "❌ Error: Private key file not found: $key_path"
            exit 1
        fi

        echo ""
        echo "✅ Certificate files found!"
        echo ""
        echo "Add these lines to your .env file:"
        echo "USE_SSL=true"
        echo "SSL_CERT_PATH=$cert_path"
        echo "SSL_KEY_PATH=$key_path"
        ;;

    *)
        echo "❌ Invalid choice"
        exit 1
        ;;
esac

echo ""
echo "=========================================="
echo "Next steps:"
echo "=========================================="
echo "1. Update your .env file with SSL settings"
echo "2. Run the HTTPS server:"
echo "   python server_https.py"
echo ""
echo "3. Access your app at:"
echo "   https://localhost:5000"
echo "   or"
echo "   https://yourdomain.com"
echo ""

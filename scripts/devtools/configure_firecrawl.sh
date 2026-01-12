#!/bin/bash
# Firecrawl Configuration Helper Script
# This script helps you configure Firecrawl for article extraction

set -e

echo "=========================================="
echo "Firecrawl Configuration Helper"
echo "=========================================="
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "❌ .env file not found!"
    echo "Please copy .env.example to .env first:"
    echo "  cp .env.example .env"
    exit 1
fi

echo "1. Checking current Firecrawl configuration..."
echo ""

# Check for existing FIRECRAWL_API_KEY
if grep -q "^FIRECRAWL_API_KEY=" .env; then
    current_key=$(grep "^FIRECRAWL_API_KEY=" .env | cut -d'=' -f2-)
    if [ -n "$current_key" ] && [ "$current_key" != "your_api_key_here" ]; then
        echo "✅ Firecrawl API Key is already configured"
        echo "   (Key: ${current_key:0:10}...${current_key: -5})"
    else
        echo "⚠️  Firecrawl API Key is not configured"
    fi
else
    echo "⚠️  Firecrawl API Key not found in .env"
fi

echo ""
echo "2. Firecrawl Configuration Options:"
echo ""
echo "   FIRECRAWL_API_KEY       Your API key from https://www.firecrawl.dev"
echo "   FIRECRAWL_API_URL       API endpoint (default: https://api.firecrawl.dev)"
echo "   FIRECRAWL_TIMEOUT       Request timeout in seconds (default: 30)"
echo ""

read -p "Do you want to configure Firecrawl now? (y/n) " -n 1 -r
echo ""

if [[ $REPLY =~ ^[Yy]$ ]]; then
    echo ""
    echo "Please enter your Firecrawl API Key:"
    echo "(Get it from: https://www.firecrawl.dev)"
    read -p "API Key: " api_key
    
    if [ -n "$api_key" ]; then
        # Backup .env file
        cp .env .env.backup.$(date +%Y%m%d_%H%M%S)
        
        # Check if FIRECRAWL_API_KEY already exists
        if grep -q "^FIRECRAWL_API_KEY=" .env; then
            # Replace existing key
            sed -i "s|^FIRECRAWL_API_KEY=.*|FIRECRAWL_API_KEY=$api_key|" .env
        else
            # Add new key at the end of file
            echo "" >> .env
            echo "# Firecrawl Configuration" >> .env
            echo "FIRECRAWL_API_KEY=$api_key" >> .env
        fi
        
        echo ""
        echo "✅ Firecrawl API Key has been configured!"
        echo ""
        
        # Show current configuration
        echo "Current Firecrawl configuration:"
        grep "^FIRECRAWL_" .env | while IFS= read -r line; do
            if [[ $line == *"API_KEY="* ]]; then
                key=$(echo "$line" | cut -d'=' -f2-)
                echo "FIRECRAWL_API_KEY=${key:0:10}...${key: -5}"
            else
                echo "$line"
            fi
        done
        
        echo ""
        echo "Note: Firecrawl is the third strategy in the extraction pipeline."
        echo "It will only be used if newspaper3k and Jina AI both fail."
        
    else
        echo "❌ No API key provided. Skipping configuration."
    fi
else
    echo "Configuration cancelled."
fi

echo ""
echo "=========================================="
echo "Configuration complete!"
echo "=========================================="

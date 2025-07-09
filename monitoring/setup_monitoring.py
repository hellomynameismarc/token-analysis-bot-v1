#!/usr/bin/env python3
"""
Monitoring Setup Script for Token Sentiment Bot

This script helps configure uptime monitoring with various free services.
"""

import os
import sys
import yaml
import json
import requests
from typing import Dict, Any, Optional
from urllib.parse import urljoin


class MonitoringSetup:
    """Helper class for setting up monitoring services."""
    
    def __init__(self, config_path: str = "monitoring/uptime_config.yaml"):
        """Initialize monitoring setup."""
        self.config_path = config_path
        self.config = self._load_config()
        
    def _load_config(self) -> Dict[str, Any]:
        """Load monitoring configuration."""
        try:
            with open(self.config_path, 'r') as f:
                return yaml.safe_load(f)
        except FileNotFoundError:
            print(f"❌ Configuration file not found: {self.config_path}")
            sys.exit(1)
        except yaml.YAMLError as e:
            print(f"❌ Error parsing configuration: {e}")
            sys.exit(1)
    
    def setup_uptimerobot(self, domain: str, api_key: Optional[str] = None) -> bool:
        """Set up UptimeRobot monitoring."""
        print("🚀 Setting up UptimeRobot monitoring...")
        
        # Health check URL
        health_url = f"https://{domain}/health"
        
        if not api_key:
            print("📝 UptimeRobot Setup Instructions:")
            print("1. Go to https://uptimerobot.com/")
            print("2. Sign up for a free account")
            print("3. Create a new monitor:")
            print(f"   - URL: {health_url}")
            print("   - Type: HTTP(s)")
            print("   - Interval: 5 minutes")
            print("   - Alert: Email/SMS")
            print("4. Copy your API key")
            print("5. Run this script again with --uptimerobot-api-key YOUR_KEY")
            return False
        
        # API endpoint for creating monitors
        api_url = "https://api.uptimerobot.com/v2/newMonitor"
        
        monitor_data = {
            "api_key": api_key,
            "format": "json",
            "type": 1,  # HTTP(s)
            "url": health_url,
            "friendly_name": "Token Sentiment Bot Health",
            "interval": 300,  # 5 minutes
            "alert_contacts": "0",  # Default alert contact
            "sub_type": 1,  # HTTP
            "port": 443,
            "keyword_type": 0,
            "keyword_value": "",
            "post_type": 1,
            "post_value": "",
            "post_content_type": "application/json"
        }
        
        try:
            response = requests.post(api_url, data=monitor_data)
            result = response.json()
            
            if result.get("stat") == "ok":
                print("✅ UptimeRobot monitor created successfully!")
                print(f"   Monitor ID: {result.get('monitor', {}).get('id')}")
                return True
            else:
                print(f"❌ Failed to create UptimeRobot monitor: {result.get('error', {}).get('message')}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up UptimeRobot: {e}")
            return False
    
    def setup_pingdom(self, domain: str, api_key: Optional[str] = None) -> bool:
        """Set up Pingdom monitoring."""
        print("🚀 Setting up Pingdom monitoring...")
        
        health_url = f"https://{domain}/health"
        
        if not api_key:
            print("📝 Pingdom Setup Instructions:")
            print("1. Go to https://www.pingdom.com/")
            print("2. Sign up for a free account")
            print("3. Create a new HTTP check:")
            print(f"   - URL: {health_url}")
            print("   - Interval: 1 minute")
            print("   - Alert: Email")
            print("4. Copy your API key")
            print("5. Run this script again with --pingdom-api-key YOUR_KEY")
            return False
        
        # Pingdom API endpoint
        api_url = "https://api.pingdom.com/api/3.1/checks"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        check_data = {
            "name": "Token Sentiment Bot Health",
            "host": domain,
            "type": "http",
            "url": health_url,
            "encryption": True,
            "port": 443,
            "resolution": 1,  # 1 minute
            "sendnotificationwhendown": 1,
            "notifyagainevery": 0,
            "notifywhenbackup": 1
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=check_data)
            
            if response.status_code == 200:
                print("✅ Pingdom check created successfully!")
                return True
            else:
                print(f"❌ Failed to create Pingdom check: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up Pingdom: {e}")
            return False
    
    def setup_statuscake(self, domain: str, api_key: Optional[str] = None) -> bool:
        """Set up StatusCake monitoring."""
        print("🚀 Setting up StatusCake monitoring...")
        
        health_url = f"https://{domain}/health"
        
        if not api_key:
            print("📝 StatusCake Setup Instructions:")
            print("1. Go to https://www.statuscake.com/")
            print("2. Sign up for a free account")
            print("3. Create a new test:")
            print(f"   - URL: {health_url}")
            print("   - Test type: HTTP")
            print("   - Check rate: 5 minutes")
            print("   - Alert: Email")
            print("4. Copy your API key")
            print("5. Run this script again with --statuscake-api-key YOUR_KEY")
            return False
        
        # StatusCake API endpoint
        api_url = "https://api.statuscake.com/v1/uptime"
        
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        
        test_data = {
            "name": "Token Sentiment Bot Health",
            "website_url": health_url,
            "test_type": "HTTP",
            "check_rate": 300,  # 5 minutes
            "contact_group": [],
            "paused": False,
            "timeout": 30,
            "confirmation": 2,
            "tags": "token-sentiment-bot"
        }
        
        try:
            response = requests.post(api_url, headers=headers, json=test_data)
            
            if response.status_code == 201:
                print("✅ StatusCake test created successfully!")
                return True
            else:
                print(f"❌ Failed to create StatusCake test: {response.text}")
                return False
                
        except Exception as e:
            print(f"❌ Error setting up StatusCake: {e}")
            return False
    
    def generate_health_check_script(self, domain: str) -> str:
        """Generate a simple health check script."""
        script = f"""#!/bin/bash
# Health Check Script for Token Sentiment Bot
# Domain: {domain}

HEALTH_URL="https://{domain}/health"
READY_URL="https://{domain}/ready"
METRICS_URL="https://{domain}/metrics"

echo "🔍 Checking Token Sentiment Bot health..."

# Check basic health
echo "📊 Health Check:"
if curl -f -s "$HEALTH_URL" | grep -q "OK"; then
    echo "✅ Health: OK"
else
    echo "❌ Health: FAILED"
    exit 1
fi

# Check readiness
echo "📋 Readiness Check:"
if curl -f -s "$READY_URL" | grep -q "READY"; then
    echo "✅ Readiness: READY"
else
    echo "❌ Readiness: NOT READY"
    exit 1
fi

# Get metrics
echo "📈 Metrics:"
curl -s "$METRICS_URL" | jq '.memory_usage, .uptime_seconds, .status' 2>/dev/null || echo "Metrics unavailable"

echo "🎉 All health checks passed!"
"""
        return script
    
    def setup_all(self, domain: str, services: Optional[Dict[str, str]] = None) -> bool:
        """Set up all monitoring services."""
        print("🚀 Setting up monitoring for Token Sentiment Bot...")
        print(f"🌐 Domain: {domain}")
        print()
        
        success = True
        
        # Set up each service
        if services and services.get("uptimerobot"):
            success &= self.setup_uptimerobot(domain, services["uptimerobot"])
        
        if services and services.get("pingdom"):
            success &= self.setup_pingdom(domain, services["pingdom"])
        
        if services and services.get("statuscake"):
            success &= self.setup_statuscake(domain, services["statuscake"])
        
        # Generate health check script
        script_content = self.generate_health_check_script(domain)
        script_path = "health_check.sh"
        
        with open(script_path, 'w') as f:
            f.write(script_content)
        
        os.chmod(script_path, 0o755)
        print(f"📝 Health check script created: {script_path}")
        
        # Print manual setup instructions
        if not services:
            print("\n📋 Manual Setup Instructions:")
            print("1. Choose a monitoring service (UptimeRobot, Pingdom, StatusCake)")
            print("2. Sign up for a free account")
            print("3. Create a new monitor/check with these settings:")
            print(f"   - URL: https://{domain}/health")
            print("   - Expected response: OK")
            print("   - Check interval: 5 minutes")
            print("4. Set up email/SMS alerts")
            print("5. Test the monitoring")
        
        return success


def main():
    """Main function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Set up monitoring for Token Sentiment Bot")
    parser.add_argument("domain", help="Your bot's domain (e.g., your-app.railway.app)")
    parser.add_argument("--uptimerobot-api-key", help="UptimeRobot API key")
    parser.add_argument("--pingdom-api-key", help="Pingdom API key")
    parser.add_argument("--statuscake-api-key", help="StatusCake API key")
    
    args = parser.parse_args()
    
    # Create monitoring setup
    setup = MonitoringSetup()
    
    # Collect API keys
    services = {}
    if args.uptimerobot_api_key:
        services["uptimerobot"] = args.uptimerobot_api_key
    if args.pingdom_api_key:
        services["pingdom"] = args.pingdom_api_key
    if args.statuscake_api_key:
        services["statuscake"] = args.statuscake_api_key
    
    # Set up monitoring
    success = setup.setup_all(args.domain, services if services else None)
    
    if success:
        print("\n🎉 Monitoring setup completed successfully!")
    else:
        print("\n⚠️ Some monitoring services failed to set up. Check the errors above.")
        sys.exit(1)


if __name__ == "__main__":
    main() 
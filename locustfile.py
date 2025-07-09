"""
Load Testing Configuration for Token Sentiment Bot

This file configures Locust load testing to simulate multiple concurrent users
sending requests to the Telegram bot's webhook endpoint.

Features:
- Simulates realistic Telegram update payloads
- Configurable user count and spawn rate
- Random user IDs and message content
- Realistic wait times between requests

Usage:
    locust -f locustfile.py --headless -u 50 -r 10 -H http://localhost:8000
    
Parameters:
    -u: Number of concurrent users to simulate
    -r: Spawn rate (users per second)
    -H: Base URL of the bot (webhook endpoint)
    --headless: Run without web UI (for CI/CD)
"""

from locust import HttpUser, task, between
import random
import string

# Configuration - adjust these to match your deployed bot's webhook path
WEBHOOK_PATH = "/webhook"

def random_user_id() -> int:
    """Generate a random Telegram user ID for load testing."""
    return random.randint(10000, 99999)


def random_message() -> str:
    """Generate a random message text for load testing."""
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))


class TelegramBotUser(HttpUser):
    """
    Locust user class that simulates Telegram bot users.
    
    This class generates realistic Telegram update payloads and sends them
    to the bot's webhook endpoint to test performance under load.
    """
    
    wait_time = between(1, 3)  # Simulate realistic user think time (1-3s)

    @task
    def send_message(self):
        """Send a simulated Telegram message to the bot's webhook."""
        # Create a realistic Telegram update payload
        payload = {
            "update_id": random.randint(100000, 999999),
            "message": {
                "message_id": random.randint(1, 1000),
                "from": {"id": random_user_id(), "is_bot": False, "first_name": "TestUser"},
                "chat": {"id": random_user_id(), "type": "private"},
                "date": 1680000000,  # Fixed timestamp for consistency
                "text": random_message(),
            },
        }
        
        # Send POST request to webhook endpoint
        self.client.post(WEBHOOK_PATH, json=payload)

# Usage:
# 1. Run your bot locally (ensure it listens for POSTs at /webhook)
# 2. In another terminal: locust -f locustfile.py --headless -u 50 -r 10 -H http://localhost:8000
#    -u: number of users (concurrent)
#    -r: spawn rate (users/sec)
#    -H: host (your bot's base URL)
# 3. See results in terminal or web UI (if not using --headless) 
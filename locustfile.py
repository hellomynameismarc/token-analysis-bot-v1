from locust import HttpUser, task, between
import random
import string

# Adjust these to match your deployed bot's webhook path
WEBHOOK_PATH = "/webhook"

# Dummy Telegram update payload (minimal valid structure)
def random_user_id():
    return random.randint(10000, 99999)

def random_message():
    return ''.join(random.choices(string.ascii_letters + string.digits, k=10))

class TelegramBotUser(HttpUser):
    wait_time = between(1, 3)  # Simulate user think time (1-3s)

    @task
    def send_message(self):
        payload = {
            "update_id": random.randint(100000, 999999),
            "message": {
                "message_id": random.randint(1, 1000),
                "from": {"id": random_user_id(), "is_bot": False, "first_name": "TestUser"},
                "chat": {"id": random_user_id(), "type": "private"},
                "date": 1680000000,
                "text": random_message(),
            },
        }
        self.client.post(WEBHOOK_PATH, json=payload)

# Usage:
# 1. Run your bot locally (ensure it listens for POSTs at /webhook)
# 2. In another terminal: locust -f locustfile.py --headless -u 50 -r 10 -H http://localhost:8000
#    -u: number of users (concurrent)
#    -r: spawn rate (users/sec)
#    -H: host (your bot's base URL)
# 3. See results in terminal or web UI (if not using --headless) 
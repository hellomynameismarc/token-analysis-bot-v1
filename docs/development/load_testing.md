# Load Testing

## Overview

The Token Sentiment Bot uses **Locust** for load testing, simulating multiple concurrent users to validate performance under load.

## Configuration

The load testing is configured in `locustfile.py` and simulates:
- **Realistic Telegram update payloads**
- **Random user IDs and message content**
- **Configurable user count and spawn rate**
- **Realistic wait times between requests**

## Running Load Tests

### Prerequisites
1. Install Locust: `pip install locust`
2. Ensure your bot is running and accessible
3. Verify the webhook endpoint is `/webhook`

### Basic Load Test
```bash
# Simulate 50 concurrent users, spawning 10 per second
locust -f locustfile.py --headless -u 50 -r 10 -H http://localhost:8000
```

### Interactive Mode
```bash
# Start Locust web interface
locust -f locustfile.py -H http://localhost:8000
```
Then open http://localhost:8089 in your browser.

### Custom Parameters
```bash
# Different user count and spawn rate
locust -f locustfile.py --headless -u 100 -r 20 -H http://localhost:8000

# Longer test duration
locust -f locustfile.py --headless -u 50 -r 10 -H http://localhost:8000 --run-time 5m
```

## Test Scenarios

### TelegramBotUser Class
The main test class that simulates Telegram users:

```python
class TelegramBotUser(HttpUser):
    wait_time = between(1, 3)  # Realistic user think time
    
    @task
    def send_message(self):
        # Send simulated Telegram update to webhook
        payload = {...}
        self.client.post(WEBHOOK_PATH, json=payload)
```

### Payload Structure
Each request sends a realistic Telegram update:
```json
{
  "update_id": 123456,
  "message": {
    "message_id": 789,
    "from": {"id": 12345, "is_bot": false, "first_name": "TestUser"},
    "chat": {"id": 12345, "type": "private"},
    "date": 1680000000,
    "text": "random_message"
  }
}
```

## Performance Targets

- **Response Time**: <7 seconds median
- **Concurrent Users**: 50+ without degradation
- **Error Rate**: <1% under normal load
- **Throughput**: 10+ requests per second

## Interpreting Results

### Key Metrics
- **RPS**: Requests per second
- **Response Time**: Average, median, 95th percentile
- **Error Rate**: Percentage of failed requests
- **User Count**: Number of concurrent users

### Example Output
```
Type     Name              # reqs      # fails |    Avg     Min     Max    Median |   req/s  failures/s
--------|----------------|-----------|---------|---------|-------|-------|--------|---------|---------
POST     /webhook             1000         0(0.00%) |    245    120    890      220 |    10.00     0.00
--------|----------------|-----------|---------|---------|-------|-------|--------|---------|---------
         Aggregated           1000         0(0.00%) |    245    120    890      220 |    10.00     0.00
```

## Troubleshooting

### Common Issues
1. **Connection Refused**: Ensure bot is running and accessible
2. **404 Errors**: Verify webhook path is correct
3. **High Error Rate**: Check bot logs for issues
4. **Slow Response**: Monitor bot performance and resources

### Debug Mode
```bash
# Run with verbose output
locust -f locustfile.py --headless -u 5 -r 1 -H http://localhost:8000 --loglevel DEBUG
```

## Integration with CI/CD

Load tests can be integrated into CI/CD pipelines:
```yaml
- name: Run Load Tests
  run: |
    # Start bot in background
    python -m bot.main &
    sleep 10
    
    # Run load test
    locust -f locustfile.py --headless -u 10 -r 2 -H http://localhost:8000 --run-time 1m
``` 
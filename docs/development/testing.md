# Testing

## Overview

The Token Sentiment Bot includes a comprehensive test suite with **150+ tests** achieving **77% code coverage**.

## Test Structure

```
tests/
├── test_sentiment_engine.py    # Core sentiment analysis tests
├── test_data_sources.py        # API integration tests
├── test_validation.py          # Address validation tests
├── test_bot_integration.py     # Bot functionality tests
├── test_cache.py               # Caching system tests
├── test_http_utils.py          # HTTP utilities tests
└── test_rate_limit.py          # Rate limiting tests
```

## Running Tests

### All Tests
```bash
python -m pytest tests/ -v
```

### With Coverage
```bash
python -m pytest --cov=core --cov=bot --cov-report=term-missing
```

### Specific Test Categories
```bash
# Sentiment engine tests
python -m pytest tests/test_sentiment_engine.py -v

# Integration tests
python -m pytest tests/test_data_sources.py -v

# Bot tests
python -m pytest tests/test_bot_integration.py -v
```

## Test Categories

### Unit Tests
- **Data Models**: Pydantic model validation and calculations
- **Business Logic**: Sentiment scoring, confidence calculation
- **Utilities**: Address validation, HTTP retries, caching

### Integration Tests
- **API Wrappers**: Mocked external API calls (Twitter, Nansen, CoinGecko)
- **Cache Integration**: Redis and in-memory cache behavior
- **Bot Commands**: Telegram bot command handling

### Edge Cases
- **No Data Scenarios**: Missing pillar data handling
- **Error Conditions**: API failures, network timeouts
- **Boundary Values**: Extreme sentiment scores, market caps

## Coverage Report

Current coverage breakdown:
- `core/sentiment_engine.py`: 82%
- `core/data_sources.py`: 86%
- `core/cache.py`: 93%
- `core/http_utils.py`: 95%
- `core/rate_limiter.py`: 98%
- `core/validation.py`: 88%
- `bot/main.py`: 39%

## CI/CD Integration

Tests run automatically on:
- **Push to main branch**
- **Pull requests**
- **Coverage reporting** to Codecov

## Best Practices

1. **Test Naming**: Descriptive test names that explain the scenario
2. **Mocking**: Use mocks for external dependencies
3. **Edge Cases**: Test boundary conditions and error scenarios
4. **Async Testing**: Proper async/await patterns for async functions
5. **Isolation**: Each test should be independent and not affect others 
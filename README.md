# Quantasaurus Rex 🦕

A daily portfolio analysis and recommendation system powered by AI that generates comprehensive investment reports based on your Robinhood portfolio.

## Features

- **Daily Analysis**: Automated portfolio analysis at 9AM ET every day
- **AI-Powered Insights**: ReAct agent using OpenAI's gpt4.1 model
- **Multi-Source Data**: Integrates Robinhood API, Aiera API, and Tavily search
- **Comprehensive Reports**: Technical analysis, sentiment analysis, and risk assessment
- **Clean Email Reports**: Minimal, aesthetically pleasing HTML email reports
- **AWS Cloud Native**: Built with AWS Lambda, EventBridge, and SES

## Architecture

```
EventBridge (9AM ET daily) → Lambda Function → [Data Sources] → ReAct Agent → Email Report
```

## Setup

### Prerequisites

- Python 3.11+
- Poetry for dependency management
- AWS CLI configured
- Node.js and npm (for CDK)

### Installation

1. Clone the repository:
```bash
git clone https://github.com/jacquelinegarrahan/quantasaurus-rex.git
cd quantasaurus-rex
```

2. Install dependencies:
```bash
poetry install
```

3. Set up environment variables:
```bash
cp .env.example .env
# Edit .env with your API keys and configuration
```

**Note:** The application automatically loads environment variables from the `.env` file when available. This works for both local testing and development.

4. Install CDK dependencies:
```bash
cd cdk
npm install
```

### Configuration

Edit `.env` file with your credentials:

- **OpenAI API Key**: Get from OpenAI platform
- **Tavily API Key**: Get from Tavily for web search
- **Aiera API Key**: Get from Aiera for financial data
- **Robinhood Credentials**: Your Robinhood username and password
- **Email Configuration**: SES-verified email addresses

### Robinhood Authentication

On first run, you'll need to complete device authentication:

1. Run the application locally first
2. Follow the device authentication prompts
3. The device ID will be stored for future use

## Local Development

### Running Tests

```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test types
poetry run pytest -m unit
poetry run pytest -m integration
```

### Usage

```python
from src.utils.retry import openai_retry

@openai_retry(max_retries=5, base_delay=2.0, max_delay=60.0)
async def my_openai_call():
    # Your OpenAI API call here
    return await client.chat.completions.create(...)
```

### Local Testing

The local test script automatically loads environment variables from the `.env` file, making it easy to test with real API keys without setting system environment variables.

```bash
# Run portfolio analysis locally with mock services
poetry run python scripts/local_test.py

# Run with real APIs (requires all environment variables in .env file)
poetry run python scripts/local_test.py --no-mocks

# Run health check only
poetry run python scripts/local_test.py --test-type health

# Run with verbose logging
poetry run python scripts/local_test.py --verbose
```

### Running Lambda Locally

The Lambda function can be run locally for development and testing:

```bash
# Quick test with mocks (recommended for development)
poetry run python scripts/local_test.py

# Full test with real APIs
poetry run python scripts/local_test.py --no-mocks --verbose
```

**Local Test Options:**
- `--test-type`: Choose `full` (default) or `health` check
- `--no-mocks`: Use real API services instead of mocks
- `--verbose`: Enable detailed logging

**Mock Services:**
When running locally with mocks (default), the script will:
- Create sample portfolio data (AAPL, GOOGL, BTC)
- Mock API responses from Robinhood, Aiera, and Tavily
- Generate a complete analysis report
- Save HTML and JSON reports to local files instead of sending emails

**Real API Testing:**
To test with real APIs, ensure all environment variables are set:
- `OPENAI_API_KEY`: Required for AI analysis
- `ROBINHOOD__USERNAME` and `ROBINHOOD__PASSWORD`: For portfolio data
- `TAVILY_API_KEY`: For news and sentiment
- `AIERA_API_KEY`: For financial data
- `EMAIL_SENDER`: For email reports (still saved to files locally)

**Note:** Even when using real APIs with `--no-mocks`, email reports are always saved to local files in the `output/` directory instead of being sent via email. This prevents accidental email sending during local development.

**Example Output:**
```
2024-01-01 09:00:00 - Starting local test: full
2024-01-01 09:00:01 - Setting up mock services...
2024-01-01 09:00:02 - Mock: Authenticating with Robinhood...
2024-01-01 09:00:03 - Mock: Fetching portfolio data...
2024-01-01 09:00:04 - Mock: Saving email report to file instead of sending...
2024-01-01 09:00:05 - Test completed successfully

==================================================
SAVED FILES
==================================================
📄 portfolio_report_20240101_090005.html
📄 portfolio_report_20240101_090005.json

📁 All files saved to: /path/to/quantasaurus-rex/output
```

### Code Quality

```bash
# Format code
poetry run black .

# Lint code
poetry run ruff check .

# Type checking
poetry run mypy src/
```

## Deployment

### AWS Infrastructure

1. Bootstrap CDK (first time only):
```bash
cd cdk
npx cdk bootstrap
```

2. Deploy infrastructure:
```bash
npx cdk deploy
```

### Environment Variables

Set the following environment variables in your deployment environment:

- All variables from `.env.example`
- AWS credentials and permissions

## Usage

Once deployed, the system will:

1. **Daily Execution**: Run automatically at 9AM ET via EventBridge
2. **Data Collection**: Fetch portfolio data from Robinhood
3. **Analysis**: Perform comprehensive analysis using AI agent
4. **Email Report**: Send formatted report to configured email

## Project Structure

```
quantasaurus-rex/
├── src/                       # Source code
│   ├── config/               # Configuration management
│   ├── models/               # Pydantic data models
│   ├── services/             # Business logic services
│   ├── utils/                # Utility functions
│   └── lambda_handler.py     # Lambda entry point
├── cdk/                      # AWS CDK infrastructure
├── tests/                    # Test files
├── scripts/                  # Utility scripts
├── assets/                   # Static assets
└── pyproject.toml           # Project configuration
```

## API Integrations

### Robinhood API
- Portfolio positions (stocks and crypto)
- Stock fundamentals
- Historical price data
- Device-based authentication

### Aiera API
- Company information and events
- Earnings data and transcripts
- Financial analysis

### Tavily Search
- Recent news and sentiment
- Market analysis
- Web search capabilities

## AI Analysis

The ReAct agent performs:

- **Technical Analysis**: Chart patterns, indicators, trends
- **Sentiment Analysis**: News and social media sentiment
- **Event Analysis**: Upcoming events and earnings
- **Risk Assessment**: Portfolio risk evaluation
- **Recommendations**: BUY/SELL/HOLD with reasoning

## Security

- API keys stored in AWS Parameter Store
- Minimal IAM permissions
- Encrypted data in transit and at rest
- Device-based authentication for Robinhood

## Monitoring

- CloudWatch logs and metrics
- Error tracking and alerting
- Performance monitoring
- Success/failure rates

## License

MIT License - see LICENSE file for details

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For issues and questions, please open a GitHub issue.
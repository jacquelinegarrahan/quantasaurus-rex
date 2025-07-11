# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Quantasaurus Rex is a daily portfolio analysis and recommendation system that generates comprehensive AI-powered investment reports. It's built as a serverless AWS application using Lambda, EventBridge, and SES, with a ReAct agent powered by OpenAI's o3 model for investment analysis.

## Key Architecture

### Core Structure
- `src/` - Main application code
  - `config/` - Configuration and settings management
  - `models/` - Pydantic data models (Portfolio, Analysis, Report)
  - `services/` - Business logic services (API clients, ReAct agent)
  - `utils/` - Shared utilities (retry logic, authentication, data processing)
  - `lambda_handler.py` - AWS Lambda entry point
- `cdk/` - AWS CDK infrastructure as code (TypeScript)
- `scripts/` - Development and deployment scripts
- `tests/` - Test files with unit and integration tests
- `assets/` - Static assets (email templates)

### Service Architecture
The application follows a layered architecture:
1. **Lambda Handler** - AWS Lambda entry point and orchestration
2. **ReAct Agent** - AI-powered analysis using LangChain and OpenAI
3. **Service Layer** - API integrations (Robinhood, Aiera, Tavily)
4. **Model Layer** - Pydantic models for data validation and structure
5. **Infrastructure** - AWS CDK stack for serverless deployment

### Key Components
- **ReAct Agent** (`src/services/react_agent.py`) - Core AI agent using LangChain/LangGraph
- **API Services** - Robinhood (portfolio), Aiera (financial data), Tavily (news/sentiment)
- **Retry Logic** (`src/utils/retry.py`) - Exponential backoff for OpenAI API calls
- **Email Service** - SES integration for HTML report delivery

## Development Commands

### Environment Setup
```bash
# Install dependencies
poetry install

# Install CDK dependencies
cd cdk && npm install
```

### Local Development
```bash
# Run portfolio analysis locally with mock services (recommended for development)
poetry run python scripts/local_test.py

# Run with real APIs (requires all environment variables in .env file)
poetry run python scripts/local_test.py --no-mocks --verbose

# Run health check only
poetry run python scripts/local_test.py --test-type health
```

### Testing
```bash
# Run all tests
poetry run pytest

# Run with coverage
poetry run pytest --cov=src

# Run specific test types
poetry run pytest -m unit
poetry run pytest -m integration

# Run specific test file
poetry run pytest tests/test_lambda_handler.py
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

### Deployment
```bash
# CDK commands (run from cdk/ directory)
cd cdk
npm run build          # Compile TypeScript
npm run deploy         # Build and deploy
npm run diff           # Show deployment diff
npm run synth          # Synthesize CloudFormation
npx cdk bootstrap      # Bootstrap CDK (first time only)
```

## Configuration

### Environment Variables
- `OPENAI_API_KEY` - OpenAI API key for ReAct agent
- `ROBINHOOD__USERNAME` / `ROBINHOOD__PASSWORD` - Robinhood authentication
- `TAVILY_API_KEY` - Tavily search API key
- `AIERA_API_KEY` - Aiera financial data API key
- `EMAIL_SENDER` / `EMAIL_RECIPIENT` - SES email configuration
- `ROBINHOOD__DEVICE_ID` - Robinhood device authentication token

### Parallel Processing Configuration
- `ENABLE_PARALLEL_PROCESSING` - Enable/disable parallel processing (default: true)
- `MAX_CONCURRENT_ANALYSES` - Maximum concurrent asset analyses (default: 10)
- `API_RATE_LIMIT_DELAY` - Base delay between API calls in seconds (default: 1.0)
- `BATCH_DELAY` - Delay between processing batches in seconds (default: 2.0)
- `STAGGER_DELAY` - Delay between starting individual tasks in seconds (default: 0.1)

### Local Development
- Environment variables loaded from `.env` file automatically
- Mock services used by default in local testing
- Real API testing available with `--no-mocks` flag
- HTML reports saved to `output/` directory during local development

## AI Analysis Features

The ReAct agent performs comprehensive analysis including:
- **Technical Analysis** - Chart patterns, indicators, trends
- **Sentiment Analysis** - News and social media sentiment
- **Event Analysis** - Upcoming events and earnings
- **Risk Assessment** - Portfolio risk evaluation
- **Recommendations** - BUY/SELL/HOLD with detailed reasoning
- **Parallel Processing** - Concurrent analysis of multiple assets using asyncio.gather()
- **Enhanced Consistency** - Improved prompting and parsing ensures recommendations align with reasoning

### Parallel Processing Architecture

The system now supports parallel processing of portfolio assets for improved performance:

- **Concurrent Analysis**: Uses asyncio.gather() to process all assets simultaneously
- **Batch Processing**: For large portfolios, processes assets in configurable batches
- **Rate Limiting**: Implements staggered delays to prevent API rate limiting
- **Graceful Degradation**: Falls back to sequential processing if parallel execution fails
- **Configurable Limits**: Maximum concurrent analyses, delays, and batch sizes are configurable

### Performance Benefits

- **Faster Analysis**: Parallel processing reduces analysis time from O(n) to O(1) for portfolios
- **Scalability**: Handles portfolios of any size with intelligent batching
- **Fault Tolerance**: Individual asset failures don't stop the entire analysis

## API Integrations

### Robinhood API
- Portfolio positions (stocks and crypto)
- Stock fundamentals and historical data
- Device-based authentication required

### Aiera API
- Company information and events
- Financial analysis and market data
- Corporate events and analyst coverage
- Note: Earnings reports endpoint has been removed from client implementation

### Tavily Search
- Recent news and sentiment analysis
- Market analysis and web search
- Real-time financial information

## Testing Framework

- Uses pytest with async support
- Separate unit and integration test markers
- Mock services for local development
- Coverage reporting available
- Test files follow `test_*.py` pattern

## Deployment Architecture

- **AWS Lambda** - Serverless compute for analysis
- **EventBridge** - Daily scheduling (9AM ET)
- **SES** - Email delivery for reports
- **Parameter Store** - Secure API key storage
- **CloudWatch** - Logging and monitoring
- **SNS** - Error alerting and notifications

## Error Handling

- Comprehensive retry logic with exponential backoff
- Dead letter queue for failed executions
- Graceful degradation when APIs are unavailable
- Detailed logging and error tracking
- Rate limiting protection for OpenAI API

## Key Dependencies

- **LangChain/LangGraph** - AI agent framework
- **OpenAI** - Language model for analysis
- **Pydantic** - Data validation and settings
- **Poetry** - Python dependency management
- **AWS CDK** - Infrastructure as code
- **Boto3** - AWS SDK for Python
# 🦕 Quantasaurus-Rex

**An intelligent portfolio recommendation bot that delivers daily AI-powered investment insights via email.**

Quantasaurus-Rex is a serverless AWS Lambda application that analyzes your Robinhood portfolio using multiple data sources and advanced AI to provide personalized buy/hold/sell recommendations every morning at 9 AM ET.

## 🚀 Features

- **Multi-Source Data Analysis**: Combines Robinhood portfolio data, Aiera fundamental analysis, and Tavily news sentiment
- **AI-Powered Recommendations**: Uses OpenAI's o3-2025-04-16 model with advanced reasoning for investment analysis
- **Professional Email Reports**: Clean, responsive HTML email summaries with actionable insights
- **Automated Daily Execution**: Runs automatically via AWS EventBridge at 9 AM ET
- **Risk Assessment**: Comprehensive risk analysis and position sizing recommendations
- **Portfolio Context**: Considers overall portfolio allocation and diversification

## 🚀 Quick Start

Want to test Quantasaurus-Rex locally before deploying to AWS? Follow these steps:

### 1. Clone and Setup
```bash
git clone <repository-url>
cd quantasaurus-rex

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies and create virtual environment
poetry install

# Activate virtual environment
poetry shell
```

### 2. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your API credentials
nano .env
```

**Minimum required for local testing:**
```env
ROBINHOOD_USERNAME=your_username
ROBINHOOD_PASSWORD=your_password
ROBINHOOD_MFA_CODE=your_mfa_code
OPENAI_API_KEY=your_openai_key
TAVILY_API_KEY=your_tavily_key
AIERA_API_KEY=your_aiera_key

# Local development flags
LOCAL_DEVELOPMENT=true
DRY_RUN=true
DEBUG=true
```

### 3. Start Aiera API Server
```bash
# In a separate terminal
cd aiera-api
python -m aiera_api.www.server
```

### 4. Run Local Test
```bash
# Test the complete pipeline
poetry run python lambda_function.py

# Or use the Poetry script
poetry run quantasaurus
```

**Expected output:**
```
🦕 QUANTASAURUS-REX LOCAL TEST
Starting test at: 2024-01-15 10:30:00

✅ Configuration loaded
✅ Robinhood authentication successful
✅ Data collection completed (5 positions)
✅ AI analysis completed (3 recommendations)
✅ Email content generated successfully

Status Code: 200
Execution Time: 45.23 seconds
```

### 5. Test Individual Components
```bash
# Test Robinhood connection
poetry run python -c "
from quantasaurus.data_collection.robinhood.client import RobinhoodClient
from quantasaurus.utils.config import Config
config = Config()
client = RobinhoodClient(config)
client.authenticate()
print('✅ Robinhood authentication successful!')
"

# Test other APIs
poetry run python -c "
from quantasaurus.data_collection.tavily.client import TavilyClient
from quantasaurus.utils.config import Config
config = Config()
client = TavilyClient(config)
print('✅ Tavily API ready!')
"
```

### 6. Debug Issues
```bash
# Enable detailed logging
export DEBUG=true
export LOG_LEVEL=DEBUG
poetry run python lambda_function.py

# Use mock data (no API calls)
export MOCK_DATA=true
poetry run python lambda_function.py
```

### 7. Robinhood Authentication Process
The system uses a hybrid approach with device tokens and sheriff challenges:

1. **Device Token**: System generates/loads a unique device token for your account
2. **Initial Login**: Attempts authentication with username, password, and device token
3. **Sheriff Challenge**: If triggered, validates using your MFA code
4. **Success**: Access token is obtained and device token is saved for future use

**Authentication Flow:**
- **Success Path**: Direct login with device token
- **Sheriff Challenge Path**: Login → Sheriff Challenge → MFA Validation → Retry Login
- **Persistent Storage**: Device tokens are saved to avoid repeated challenges

**Configuration Options:**
- `ROBINHOOD_MFA_CODE` - Your MFA code for sheriff challenges (required)
- `ROBINHOOD_DEVICE_APPROVAL_DELAY=30` - Seconds to wait for device approval
- `ROBINHOOD_MAX_AUTH_RETRIES=3` - Maximum authentication attempts
- `ROBINHOOD_DEVICE_STORAGE_PATH` - Custom path for device token storage (optional)

**Device Token Management:**
The system automatically stores approved device tokens in `~/.quantasaurus/robinhood_device.json` to avoid repeated approvals. To force a new device approval, delete this file or use the clear method in code.

🎯 **Local testing is perfect for development and debugging before AWS deployment!**

---

## 📋 Prerequisites

Before starting, ensure you have:

- **AWS Account** with appropriate permissions
- **Robinhood Account** with API access
- **OpenAI API Key** with access to o3-2025-04-16 model
- **Tavily API Key** for news data
- **Aiera API Access** (local deployment in aiera-api/)
- **Python 3.11+** for local development
- **AWS CLI** configured with your credentials

## 🛠️ Step-by-Step Implementation Guide

### Phase 1: Environment Setup (30 minutes)

#### 1.1 Clone and Configure Repository
```bash
# Clone the repository
git clone <repository-url>
cd quantasaurus-rex

# Install Poetry (if not already installed)
curl -sSL https://install.python-poetry.org | python3 -

# Install dependencies and create virtual environment
poetry install

# Activate virtual environment
poetry shell
```

#### 1.2 Configure Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Edit .env with your actual credentials
nano .env
```

**Required Environment Variables:**
```env
# AWS Configuration
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key

# Robinhood Credentials
ROBINHOOD_USERNAME=your_robinhood_username
ROBINHOOD_PASSWORD=your_robinhood_password
ROBINHOOD_MFA_CODE=your_mfa_code
# Device approval settings (optional)
ROBINHOOD_DEVICE_APPROVAL_DELAY=30
ROBINHOOD_MAX_AUTH_RETRIES=3

# API Keys
OPENAI_API_KEY=your_openai_api_key
TAVILY_API_KEY=your_tavily_api_key
AIERA_API_KEY=your_aiera_api_key

# Email Configuration
FROM_EMAIL=quantasaurus-rex@yourdomain.com
TO_EMAIL=jacquelinegarrahan@gmail.com
```

#### 1.3 Test Local Development
```bash
# Run local test
poetry run python lambda_function.py

# Or use the Poetry script
poetry run quantasaurus

# This will run a dry-run test of the entire pipeline
```

### Phase 2: AWS Infrastructure Setup (45 minutes)

#### 2.1 Set Up AWS SES for Email Delivery
```bash
# Verify sender email address
aws ses verify-email-identity --email-address quantasaurus-rex@yourdomain.com

# Verify recipient email address (required for sandbox mode)
aws ses verify-email-identity --email-address jacquelinegarrahan@gmail.com

# Check verification status
aws ses get-identity-verification-attributes --identities quantasaurus-rex@yourdomain.com
```

#### 2.2 Create S3 Bucket for Deployment
```bash
# Create S3 bucket for Lambda deployment packages
aws s3 mb s3://quantasaurus-rex-deployment-bucket --region us-east-1

# Create S3 bucket for application data
aws s3 mb s3://quantasaurus-rex-data --region us-east-1
```

#### 2.3 Create IAM Role for Lambda
```bash
# Create trust policy file
cat > trust-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF

# Create IAM role
aws iam create-role \
  --role-name quantasaurus-rex-lambda-role \
  --assume-role-policy-document file://trust-policy.json

# Attach basic Lambda execution policy
aws iam attach-role-policy \
  --role-name quantasaurus-rex-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole

# Create and attach SES policy
cat > ses-policy.json << EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "ses:SendEmail",
        "ses:SendRawEmail"
      ],
      "Resource": "*"
    }
  ]
}
EOF

aws iam create-policy \
  --policy-name quantasaurus-rex-ses-policy \
  --policy-document file://ses-policy.json

aws iam attach-role-policy \
  --role-name quantasaurus-rex-lambda-role \
  --policy-arn arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):policy/quantasaurus-rex-ses-policy
```

#### 2.4 Create Lambda Function
```bash
# Build deployment package with Poetry
poetry build-requirements > requirements.txt
poetry run pip install --target ./package -r requirements.txt
cd package && zip -r ../quantasaurus-rex-deployment.zip . && cd ..
zip -r quantasaurus-rex-deployment.zip quantasaurus/ lambda_function.py -x "*.git*" "*.env*" "venv/*" "__pycache__/*"

# Upload to S3
aws s3 cp quantasaurus-rex-deployment.zip s3://quantasaurus-rex-deployment-bucket/

# Create Lambda function
aws lambda create-function \
  --function-name quantasaurus-rex \
  --runtime python3.11 \
  --role arn:aws:iam::$(aws sts get-caller-identity --query Account --output text):role/quantasaurus-rex-lambda-role \
  --handler lambda_function.lambda_handler \
  --code S3Bucket=quantasaurus-rex-deployment-bucket,S3Key=quantasaurus-rex-deployment.zip \
  --timeout 900 \
  --memory-size 1024 \
  --environment Variables="{
    AWS_S3_BUCKET=quantasaurus-rex-data,
    ROBINHOOD_USERNAME=$ROBINHOOD_USERNAME,
    ROBINHOOD_PASSWORD=$ROBINHOOD_PASSWORD,
    ROBINHOOD_MFA_CODE=$ROBINHOOD_MFA_CODE,
    OPENAI_API_KEY=$OPENAI_API_KEY,
    TAVILY_API_KEY=$TAVILY_API_KEY,
    AIERA_API_KEY=$AIERA_API_KEY,
    FROM_EMAIL=$FROM_EMAIL,
    TO_EMAIL=$TO_EMAIL
  }"
```

#### 2.5 Create EventBridge Schedule
```bash
# Create EventBridge rule for daily execution at 9 AM ET
aws events put-rule \
  --name quantasaurus-rex-daily-schedule \
  --schedule-expression "cron(0 14 * * ? *)" \
  --description "Daily Quantasaurus-Rex analysis at 9 AM ET"

# Add Lambda target to the rule
aws events put-targets \
  --rule quantasaurus-rex-daily-schedule \
  --targets "Id"="1","Arn"="arn:aws:lambda:us-east-1:$(aws sts get-caller-identity --query Account --output text):function:quantasaurus-rex"

# Add permission for EventBridge to invoke Lambda
aws lambda add-permission \
  --function-name quantasaurus-rex \
  --statement-id quantasaurus-rex-eventbridge-permission \
  --action lambda:InvokeFunction \
  --principal events.amazonaws.com \
  --source-arn arn:aws:events:us-east-1:$(aws sts get-caller-identity --query Account --output text):rule/quantasaurus-rex-daily-schedule
```

### Phase 3: Component Implementation (2-3 hours)

#### 3.1 Implement Robinhood Data Collection
```bash
# Test Robinhood authentication
poetry run python -c "
from quantasaurus.data_collection.robinhood.client import RobinhoodClient
from quantasaurus.utils.config import Config
config = Config()
client = RobinhoodClient(config)
client.authenticate()
print('Robinhood authentication successful!')
"
```

#### 3.2 Configure Aiera API Integration
```bash
# Start local Aiera API server (in separate terminal)
cd aiera-api
python -m aiera_api.www.server

# Test Aiera API connection
poetry run python -c "
from quantasaurus.data_collection.aiera.client import AieraClient
from quantasaurus.utils.config import Config
config = Config()
client = AieraClient(config)
print('Aiera API connection successful!')
"
```

#### 3.3 Test Tavily News Integration
```bash
# Test Tavily API
poetry run python -c "
from quantasaurus.data_collection.tavily.client import TavilyClient
from quantasaurus.utils.config import Config
config = Config()
client = TavilyClient(config)
print('Tavily API connection successful!')
"
```

#### 3.4 Configure OpenAI Analysis Engine
```bash
# Test OpenAI API
poetry run python -c "
from quantasaurus.ai_analysis.engine import AnalysisEngine
from quantasaurus.utils.config import Config
config = Config()
engine = AnalysisEngine(config)
print('OpenAI API connection successful!')
"
```

### Phase 4: Testing and Validation (1 hour)

#### 4.1 Local End-to-End Test
```bash
# Run complete local test
poetry run python lambda_function.py

# Or use the Poetry script
poetry run quantasaurus

# Check for successful execution and email generation
```

#### 4.2 Lambda Function Testing
```bash
# Test Lambda function
aws lambda invoke \
  --function-name quantasaurus-rex \
  --payload '{"source": "test"}' \
  response.json

# Check response
cat response.json

# Check CloudWatch logs
aws logs describe-log-groups --log-group-name-prefix /aws/lambda/quantasaurus-rex
```

#### 4.3 Email Delivery Test
```bash
# Test email delivery
aws ses send-test-email \
  --source quantasaurus-rex@yourdomain.com \
  --destination ToAddresses=jacquelinegarrahan@gmail.com \
  --message Subject={Data="Test Email"},Body={Text={Data="This is a test email"}}
```

### Phase 5: Production Deployment (30 minutes)

#### 5.1 Update Lambda Function
```bash
# Create production deployment package with Poetry
poetry build-requirements > requirements.txt
poetry run pip install --target ./package -r requirements.txt
cd package && zip -r ../quantasaurus-rex-production.zip . && cd ..
zip -r quantasaurus-rex-production.zip quantasaurus/ lambda_function.py -x "*.git*" "*.env*" "__pycache__/*"

# Upload to S3
aws s3 cp quantasaurus-rex-production.zip s3://quantasaurus-rex-deployment-bucket/

# Update Lambda function
aws lambda update-function-code \
  --function-name quantasaurus-rex \
  --s3-bucket quantasaurus-rex-deployment-bucket \
  --s3-key quantasaurus-rex-production.zip
```

#### 5.2 Configure Production Environment
```bash
# Update environment variables (remove DEBUG flags)
aws lambda update-function-configuration \
  --function-name quantasaurus-rex \
  --environment Variables="{
    AWS_S3_BUCKET=quantasaurus-rex-data,
    ROBINHOOD_USERNAME=$ROBINHOOD_USERNAME,
    ROBINHOOD_PASSWORD=$ROBINHOOD_PASSWORD,
    ROBINHOOD_MFA_CODE=$ROBINHOOD_MFA_CODE,
    OPENAI_API_KEY=$OPENAI_API_KEY,
    TAVILY_API_KEY=$TAVILY_API_KEY,
    AIERA_API_KEY=$AIERA_API_KEY,
    FROM_EMAIL=$FROM_EMAIL,
    TO_EMAIL=$TO_EMAIL,
    DRY_RUN=false,
    LOCAL_DEVELOPMENT=false
  }"
```

#### 5.3 Enable Monitoring and Alerting
```bash
# Create CloudWatch alarm for Lambda errors
aws cloudwatch put-metric-alarm \
  --alarm-name quantasaurus-rex-errors \
  --alarm-description "Quantasaurus-Rex Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 1 \
  --comparison-operator GreaterThanOrEqualToThreshold \
  --dimensions Name=FunctionName,Value=quantasaurus-rex \
  --evaluation-periods 1 \
  --alarm-actions arn:aws:sns:us-east-1:$(aws sts get-caller-identity --query Account --output text):quantasaurus-rex-alerts
```

### Phase 6: Maintenance and Monitoring (Ongoing)

#### 6.1 Daily Monitoring
```bash
# Check Lambda execution logs
aws logs filter-log-events \
  --log-group-name /aws/lambda/quantasaurus-rex \
  --start-time $(date -d "1 day ago" +%s)000

# Check email delivery metrics
aws ses get-send-statistics
```

#### 6.2 Weekly Updates
```bash
# Update Lambda function with latest code
./deploy.sh

# Review and update dependencies
poetry update

# Or update specific packages
poetry add package_name@latest
```

#### 6.3 Monthly Optimization
```bash
# Analyze CloudWatch metrics
aws cloudwatch get-metric-statistics \
  --namespace AWS/Lambda \
  --metric-name Duration \
  --dimensions Name=FunctionName,Value=quantasaurus-rex \
  --start-time $(date -d "30 days ago" +%s) \
  --end-time $(date +%s) \
  --period 86400 \
  --statistics Average,Maximum

# Review and optimize configuration
```

## 📊 Expected Costs

### Monthly Operating Costs
- **Lambda Execution**: $5-10 (daily executions)
- **EventBridge**: $1 (daily schedule)
- **SES**: $1 (daily emails)
- **CloudWatch**: $3-5 (logging and monitoring)
- **S3**: $1-2 (temporary storage)
- **OpenAI API**: $50-100 (daily AI analysis)
- **Tavily API**: $10-20 (news searches)
- **Total**: $70-140/month

## 🔧 Troubleshooting

### Common Issues

#### Authentication Problems
```bash
# Check Robinhood credentials
poetry run python -c "from quantasaurus.data_collection.robinhood.client import RobinhoodClient; print('Testing auth...')"

# Check API keys
echo $OPENAI_API_KEY | head -c 10
echo $TAVILY_API_KEY | head -c 10
```

#### Lambda Function Issues
```bash
# Check Lambda logs
aws logs tail /aws/lambda/quantasaurus-rex --follow

# Test function locally
poetry run python lambda_function.py
```

#### Email Delivery Problems
```bash
# Check SES sending statistics
aws ses get-send-statistics

# Verify email identities
aws ses get-identity-verification-attributes \
  --identities quantasaurus-rex@yourdomain.com jacquelinegarrahan@gmail.com
```

### Debug Mode
```bash
# Enable debug mode for detailed logging
aws lambda update-function-configuration \
  --function-name quantasaurus-rex \
  --environment Variables="{...,DEBUG=true,LOG_LEVEL=DEBUG}"
```

## 🔐 Security Best Practices

1. **Never commit .env files** - Always use .env.example
2. **Use IAM roles** - Avoid hard-coding AWS credentials
3. **Rotate API keys** - Regularly update all API keys
4. **Enable MFA** - Use multi-factor authentication where available
5. **Monitor access** - Set up CloudWatch alarms for unusual activity

## 📚 Additional Resources

- [AWS Lambda Documentation](https://docs.aws.amazon.com/lambda/)
- [Robinhood API Documentation](https://robin-stocks.readthedocs.io/)
- [OpenAI API Documentation](https://platform.openai.com/docs)
- [Tavily API Documentation](https://tavily.com/docs)
- [LangChain Documentation](https://python.langchain.com/)

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## ⚠️ Disclaimer

This software is for educational and informational purposes only. It should not be considered as financial advice. Always consult with a qualified financial advisor before making investment decisions. The authors are not responsible for any financial losses incurred through the use of this software.

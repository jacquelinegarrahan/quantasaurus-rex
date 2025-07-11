# quantasaurus-rex implementation guidelines

## Description
This repository will hold the code for generating a daily report of recommendations based on a robinhood portfolio.

## Architecture and deployment:
The repository should include scripts and instructions for the aws stack as well as the core business logic:

1. Deployment to AWS infrastructure using CodeDeploy
2. Daily Event Bridge cron job at 9AM ET each day
3. Lambda function containing business logic

## Lambda function functionality:

The lambda will perform the below workflow:

1. Retrieves the following data:
* Current crypto and stock balances using the robin_stocks robinhood API
* Get fundamentals using the robin_stocks API https://robin-stocks.readthedocs.io/en/latest/robinhood.html#robin_stocks.robinhood.stocks.get_fundamentals
* Get historical price data using https://robin-stocks.readthedocs.io/en/latest/robinhood.html#robin_stocks.robinhood.stocks.get_stock_historicals for stocks and https://robin-stocks.readthedocs.io/en/latest/robinhood.html#robin_stocks.robinhood.crypto.get_crypto_historicals for crypto
* Relevant information for stocks via requests to Aiera's api. The endpoints for the API are available for reference locally in aiera-api/aiera_api/www. Please determine which of these endpoints will be useful for your purpose.
2. Search the web for recent news about crypto or stock using the tavily-python API.
3. For each stock/crypto build a report using a ReAct agent containing:
* Technical analysis
* Sentiment analysis
* Event analysis
* Risk assessment 
* Portfolio context
Use lanchain's ChatOpenAI wrapper with OpenAI's "gpt-4.1-2025-04-14" model
Include figures where relevant.
4. For each asset, create a buy/sell/hold recommendation
5. Create an email from the report and recommendations in clean, minimal, aesthetically pleasing html. 
5. Send the report email to jacquelinegarrahan@gmail.com.

## Project Setup
* Use poetry for environment management
* Use context7 mcp tools for looking up latest dependency documentation
* Include script for testing locally
* Use AWS CDK

## Python Dependencies
* pydantic for data models
* pydantic-settings for configuring environment from .env or environment variables
* robin-stocks:  https://github.com/jmfernandes/robin_stocks
* langchain
* langchain-openai
* tavily-python 

## Robinhood authentication 
* Use device approval for robinhood authentication. Reference the [robin stock modifications code](https://raw.githubusercontent.com/bhyman67/Mods-to-robin-stocks-Authentication/02e5491a9844382c5915180b7bd5321ed98a013b/Authentication.py) when implementing the client.
* Persist the device id across sessions
"""Lambda handler for Quantasaurus Rex portfolio analysis."""

import asyncio
import json
import logging
import sys
import traceback
from typing import Dict, Any, Optional
from datetime import datetime
import uuid
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Suppress LangChain Pydantic deprecation warnings
import warnings
warnings.filterwarnings("ignore", category=UserWarning, module="pydantic")
warnings.filterwarnings("ignore", message=".*langchain_core.pydantic_v1.*")
logger = logging.getLogger(__name__)

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).parent.parent / ".env"
    if env_path.exists():
        load_dotenv(env_path)
        logger.info(f"Loaded environment variables from {env_path}")
    else:
        logger.info("No .env file found, using system environment variables")
except ImportError:
    logger.info("python-dotenv not available, using system environment variables")

# Import application modules
from .config.settings import Settings
from .services.robinhood_client import RobinhoodService
from .services.aiera_client import AieraService
from .services.tavily_client import TavilyService
from .services.react_agent import QuantasaurusReactAgent
from .services.email_service import EmailService
from .models.report import Report


class QuantasaurusLambdaHandler:
    """Main Lambda handler class for portfolio analysis."""
    
    def __init__(self):
        """Initialize the handler."""
        self.settings: Optional[Settings] = None
        self.robinhood_service: Optional[RobinhoodService] = None
        self.aiera_service: Optional[AieraService] = None
        self.tavily_service: Optional[TavilyService] = None
        self.react_agent: Optional[QuantasaurusReactAgent] = None
        self.email_service: Optional[EmailService] = None
        self.execution_id: str = str(uuid.uuid4())
        self.start_time: Optional[datetime] = None
    
    async def initialize(self):
        """Initialize all services."""
        try:
            logger.info(f"Initializing Quantasaurus Rex handler (ID: {self.execution_id})")
            
            # Load settings
            self.settings = Settings()
            logger.info(f"Environment: {self.settings.environment}")
            
            # Initialize services
            self.robinhood_service = RobinhoodService(self.settings.robinhood)
            self.aiera_service = AieraService(self.settings.aiera_api_key)
            self.tavily_service = TavilyService(self.settings.tavily_api_key)
            self.react_agent = QuantasaurusReactAgent(self.settings)
            self.email_service = EmailService(self.settings)
            
            # Initialize agent with services
            await self.react_agent.initialize_services(
                self.robinhood_service,
                self.aiera_service,
                self.tavily_service
            )
            
            logger.info("Successfully initialized all services")
            
        except Exception as e:
            logger.error(f"Error initializing handler: {str(e)}")
            raise
    
    async def process_portfolio(self) -> Dict[str, Any]:
        """Main portfolio processing logic."""
        try:
            self.start_time = datetime.utcnow()
            logger.info("Starting portfolio analysis...")
            
            # Step 1: Authenticate with Robinhood
            logger.info("Authenticating with Robinhood...")
            auth_success = await self.robinhood_service.authenticate()
            if not auth_success:
                raise Exception("Failed to authenticate with Robinhood")
            
            # Step 2: Get portfolio data
            logger.info("Fetching portfolio data...")
            portfolio = await self.robinhood_service.get_portfolio()
            logger.info(f"Portfolio loaded: ${portfolio.total_value:,.2f} with {portfolio.total_positions} positions")
            
            # Step 3: Get additional data for each position
            logger.info("Fetching additional market data...")
            await self._enrich_portfolio_data(portfolio)
            
            # Step 4: Run AI analysis
            logger.info("Running AI analysis...")
            analyses = await self.react_agent.generate_portfolio_analysis(portfolio)
            logger.info(f"Completed analysis for {len(analyses)} assets")
            
            # Step 5: Create report
            logger.info("Creating portfolio report...")
            report = self._create_report(portfolio, analyses)
            
            # Step 6: Generate email
            logger.info("Generating email report...")
            html_content = self.email_service.generate_html_report(portfolio, analyses)
            
            # Step 7: Send email
            logger.info("Sending email report...")
            email_success = await self.email_service.send_report(html_content)
            
            # Calculate execution time
            execution_time = (datetime.utcnow() - self.start_time).total_seconds()
            
            # Create response
            response = {
                "statusCode": 200,
                "body": {
                    "execution_id": self.execution_id,
                    "message": "Portfolio analysis completed successfully",
                    "portfolio_value": portfolio.total_value,
                    "assets_analyzed": len(analyses),
                    "recommendations": {
                        "buy": sum(1 for a in analyses if a.recommendation.value == "BUY"),
                        "sell": sum(1 for a in analyses if a.recommendation.value == "SELL"),
                        "hold": sum(1 for a in analyses if a.recommendation.value == "HOLD")
                    },
                    "email_sent": email_success,
                    "execution_time_seconds": execution_time,
                    "timestamp": datetime.utcnow().isoformat()
                }
            }
            
            logger.info(f"Portfolio analysis completed successfully in {execution_time:.2f} seconds")
            return response
            
        except Exception as e:
            logger.error(f"Error in portfolio processing: {str(e)}")
            logger.error(traceback.format_exc())
            raise
        finally:
            # Cleanup
            await self._cleanup()
    
    async def _enrich_portfolio_data(self, portfolio):
        """Enrich portfolio with additional data."""
        try:
            # Get all symbols
            all_symbols = [pos.symbol for pos in portfolio.all_positions]
            
            # Get stock fundamentals
            stock_symbols = [pos.symbol for pos in portfolio.stocks]
            if stock_symbols:
                logger.info(f"Fetching fundamentals for {len(stock_symbols)} stocks...")
                fundamentals = await self.robinhood_service.get_stock_fundamentals(stock_symbols)
                
                # Add fundamentals to stock positions
                for stock in portfolio.stocks:
                    if stock.symbol in fundamentals:
                        stock.fundamentals = fundamentals[stock.symbol]
            
            # Get historical data
            if all_symbols:
                logger.info(f"Fetching historical data for {len(all_symbols)} symbols...")
                historical_data = await self.robinhood_service.get_historical_data(all_symbols)
                
                # Add historical data to positions
                for position in portfolio.all_positions:
                    if position.symbol in historical_data:
                        position.historical_data = historical_data[position.symbol]['data']
            
            # Get Aiera data for stocks
            for stock in portfolio.stocks:
                try:
                    aiera_data = await self.aiera_service.get_company_info(stock.symbol)
                    if aiera_data:
                        stock.aiera_data = aiera_data
                except Exception as e:
                    logger.warning(f"Failed to get Aiera data for {stock.symbol}: {str(e)}")
            
            logger.info("Successfully enriched portfolio data")
            
        except Exception as e:
            logger.error(f"Error enriching portfolio data: {str(e)}")
            # Continue with analysis even if enrichment fails
    
    def _create_report(self, portfolio, analyses) -> Report:
        """Create structured report."""
        try:
            # Calculate portfolio risk level
            risk_scores = [a.risk_assessment.risk_score for a in analyses if a.risk_assessment]
            avg_risk_score = sum(risk_scores) / len(risk_scores) if risk_scores else 0.5
            
            if avg_risk_score < 0.3:
                portfolio_risk_level = "low"
            elif avg_risk_score < 0.7:
                portfolio_risk_level = "medium"
            else:
                portfolio_risk_level = "high"
            
            # Generate risk summary
            high_risk_assets = [a.symbol for a in analyses if a.risk_assessment.risk_level in ['high', 'very_high']]
            if high_risk_assets:
                risk_summary = f"Portfolio contains {len(high_risk_assets)} high-risk assets: {', '.join(high_risk_assets[:3])}"
            else:
                risk_summary = "Portfolio risk is well-managed with balanced exposure"
            
            report = Report.create_report(
                report_id=self.execution_id,
                portfolio=portfolio,
                analyses=analyses,
                portfolio_risk_level=portfolio_risk_level,
                risk_summary=risk_summary,
                execution_time=(datetime.utcnow() - self.start_time).total_seconds() if self.start_time else None,
                data_sources_used=["robinhood", "aiera", "tavily", "openai"],
                analysis_config={
                    "model": self.settings.openai_model,
                    "confidence_threshold": self.settings.confidence_threshold
                }
            )
            
            return report
            
        except Exception as e:
            logger.error(f"Error creating report: {str(e)}")
            raise
    
    async def _cleanup(self):
        """Cleanup resources."""
        try:
            if self.robinhood_service:
                await self.robinhood_service.logout()
            
            if self.aiera_service:
                await self.aiera_service.close()
            
            if self.email_service:
                await self.email_service.close()
            
            logger.info("Cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {str(e)}")
    
    async def health_check(self) -> Dict[str, Any]:
        """Health check endpoint."""
        try:
            await self.initialize()
            
            # Test basic functionality
            health_status = {
                "status": "healthy",
                "timestamp": datetime.utcnow().isoformat(),
                "version": "1.0.0",
                "services": {
                    "robinhood": "available",
                    "aiera": "available",
                    "tavily": "available",
                    "openai": "available",
                    "ses": "available" if self.email_service.ses_client else "unavailable"
                }
            }
            
            return {
                "statusCode": 200,
                "body": health_status
            }
            
        except Exception as e:
            logger.error(f"Health check failed: {str(e)}")
            return {
                "statusCode": 500,
                "body": {
                    "status": "unhealthy",
                    "error": str(e),
                    "timestamp": datetime.utcnow().isoformat()
                }
            }


# Global handler instance
handler_instance = QuantasaurusLambdaHandler()


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Lambda handler entry point."""
    try:
        logger.info(f"Lambda invoked with event: {json.dumps(event, default=str)}")
        
        # Check if this is a health check
        if event.get("source") == "health-check" or event.get("httpMethod") == "GET":
            return asyncio.run(handler_instance.health_check())
        
        # Check if this is a scheduled event (EventBridge)
        if event.get("source") == "aws.events":
            logger.info("Processing scheduled portfolio analysis...")
            return asyncio.run(process_scheduled_analysis())
        
        # Default portfolio analysis
        return asyncio.run(process_scheduled_analysis())
        
    except Exception as e:
        logger.error(f"Lambda handler error: {str(e)}")
        logger.error(traceback.format_exc())
        
        return {
            "statusCode": 500,
            "body": {
                "error": str(e),
                "message": "Portfolio analysis failed",
                "timestamp": datetime.utcnow().isoformat(),
                "execution_id": handler_instance.execution_id
            }
        }


async def process_scheduled_analysis() -> Dict[str, Any]:
    """Process scheduled portfolio analysis."""
    try:
        # Initialize handler
        await handler_instance.initialize()
        
        # Process portfolio
        result = await handler_instance.process_portfolio()
        
        logger.info("Scheduled analysis completed successfully")
        return result
        
    except Exception as e:
        logger.error(f"Scheduled analysis failed: {str(e)}")
        raise


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """Alternative entry point for AWS Lambda."""
    return handler(event, context)


# For local testing
if __name__ == "__main__":
    # Test the handler locally
    test_event = {
        "source": "test",
        "detail-type": "Scheduled Event",
        "detail": {}
    }
    
    class MockContext:
        def __init__(self):
            self.function_name = "quantasaurus-rex-local"
            self.memory_limit_in_mb = 1024
            self.invoked_function_arn = "arn:aws:lambda:us-east-1:123456789012:function:quantasaurus-rex-local"
            self.aws_request_id = "local-test-request-id"
    
    try:
        result = handler(test_event, MockContext())
        print(f"Local test result: {json.dumps(result, indent=2, default=str)}")
    except Exception as e:
        print(f"Local test error: {str(e)}")
        print(traceback.format_exc())
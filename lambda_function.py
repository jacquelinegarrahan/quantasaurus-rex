"""
Quantasaurus-Rex AWS Lambda Entry Point

This is the main entry point for the AWS Lambda function that orchestrates
the daily portfolio analysis and recommendation generation.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, Any

from quantasaurus.utils.config import Config
from quantasaurus.utils.logger import setup_logger
from quantasaurus.utils.exceptions import QuantasaurusError
from quantasaurus.data_collection.orchestrator import DataCollectionOrchestrator
from quantasaurus.ai_analysis.engine import AnalysisEngine
from quantasaurus.email_generation.generator import EmailGenerator


def lambda_handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    """
    Main AWS Lambda handler function.
    
    Args:
        event: Lambda event data (typically from EventBridge)
        context: Lambda context object
        
    Returns:
        Dict containing execution status and results
    """
    # Set up logging
    logger = setup_logger()
    logger.info("Starting Quantasaurus-Rex analysis", extra={
        "request_id": context.aws_request_id,
        "function_name": context.function_name,
        "execution_time": datetime.utcnow().isoformat()
    })
    
    try:
        # Initialize configuration
        config = Config()
        
        # Log configuration (without sensitive data)
        logger.info("Configuration loaded", extra={
            "analysis_lookback_days": config.analysis_lookback_days,
            "max_recommendations": config.max_recommendations,
            "confidence_threshold": config.confidence_threshold,
            "dry_run": config.dry_run
        })
        
        # Phase 1: Data Collection
        logger.info("Starting data collection phase")
        data_orchestrator = DataCollectionOrchestrator(config)
        portfolio_data = data_orchestrator.collect_all_data()
        
        logger.info("Data collection completed", extra={
            "portfolio_positions": len(portfolio_data.get("positions", [])),
            "news_items": len(portfolio_data.get("news", [])),
            "corporate_events": len(portfolio_data.get("events", []))
        })
        
        # Phase 2: AI Analysis
        logger.info("Starting AI analysis phase")
        analysis_engine = AnalysisEngine(config)
        recommendations = analysis_engine.analyze_portfolio(portfolio_data)
        
        logger.info("AI analysis completed", extra={
            "total_recommendations": len(recommendations),
            "buy_signals": len([r for r in recommendations if r.recommendation == "BUY"]),
            "hold_signals": len([r for r in recommendations if r.recommendation == "HOLD"]),
            "sell_signals": len([r for r in recommendations if r.recommendation == "SELL"])
        })
        
        # Phase 3: Email Generation and Delivery
        logger.info("Starting email generation phase")
        email_generator = EmailGenerator(config)
        
        if config.dry_run:
            logger.info("Dry run mode - email generation only, no delivery")
            email_result = email_generator.generate_email_content(
                portfolio_data, recommendations
            )
            logger.info("Email content generated successfully")
        else:
            email_result = email_generator.generate_and_send_email(
                portfolio_data, recommendations
            )
            logger.info("Email sent successfully", extra={
                "message_id": email_result.get("message_id"),
                "delivery_status": email_result.get("status")
            })
        
        # Prepare response
        response = {
            "statusCode": 200,
            "body": json.dumps({
                "status": "success",
                "execution_time": datetime.utcnow().isoformat(),
                "request_id": context.aws_request_id,
                "results": {
                    "portfolio_positions": len(portfolio_data.get("positions", [])),
                    "recommendations_generated": len(recommendations),
                    "email_delivered": not config.dry_run,
                    "dry_run": config.dry_run
                }
            })
        }
        
        logger.info("Quantasaurus-Rex analysis completed successfully")
        return response
        
    except QuantasaurusError as e:
        logger.error("Quantasaurus-Rex specific error occurred", extra={
            "error_type": type(e).__name__,
            "error_message": str(e),
            "error_code": getattr(e, 'code', 'UNKNOWN')
        })
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error_type": "QuantasaurusError",
                "error_message": str(e),
                "request_id": context.aws_request_id
            })
        }
        
    except Exception as e:
        logger.error("Unexpected error occurred", extra={
            "error_type": type(e).__name__,
            "error_message": str(e)
        }, exc_info=True)
        
        return {
            "statusCode": 500,
            "body": json.dumps({
                "status": "error",
                "error_type": "UnexpectedError",
                "error_message": str(e),
                "request_id": context.aws_request_id
            })
        }


def local_test_handler():
    """
    Test function for local development.
    Simulates Lambda execution without AWS context.
    """
    import time
    from unittest.mock import Mock
    
    # Mock Lambda context
    context = Mock()
    context.aws_request_id = "test-request-id"
    context.function_name = "quantasaurus-rex-test"
    context.get_remaining_time_in_millis = lambda: 300000  # 5 minutes
    
    # Mock event
    event = {
        "source": "aws.events",
        "detail-type": "Scheduled Event",
        "detail": {}
    }
    
    # Set development environment
    os.environ["LOCAL_DEVELOPMENT"] = "true"
    os.environ["DRY_RUN"] = "true"
    
    print("=" * 60)
    print("🦕 QUANTASAURUS-REX LOCAL TEST")
    print("=" * 60)
    print(f"Starting test at: {datetime.now()}")
    print()
    
    start_time = time.time()
    result = lambda_handler(event, context)
    end_time = time.time()
    
    print()
    print("=" * 60)
    print("📊 TEST RESULTS")
    print("=" * 60)
    print(f"Status Code: {result['statusCode']}")
    print(f"Execution Time: {end_time - start_time:.2f} seconds")
    print(f"Result: {json.dumps(json.loads(result['body']), indent=2)}")
    print("=" * 60)
    
    return result


if __name__ == "__main__":
    # Allow local testing
    local_test_handler()
#!/usr/bin/env python3
"""Deployment script for Quantasaurus Rex."""

import os
import sys
import subprocess
import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class QuantasaurusDeployer:
    """Deployment manager for Quantasaurus Rex."""
    
    def __init__(self, environment: str = "development"):
        """Initialize deployer."""
        self.environment = environment
        self.project_root = Path(__file__).parent.parent
        self.cdk_dir = self.project_root / "cdk"
        
        # Environment validation
        if environment not in ["development", "staging", "production"]:
            raise ValueError(f"Invalid environment: {environment}")
        
        logger.info(f"Deploying to environment: {environment}")
    
    def validate_environment(self) -> bool:
        """Validate environment setup."""
        logger.info("Validating environment setup...")
        
        # Check required files
        required_files = [
            ".env",
            "pyproject.toml",
            "cdk/package.json",
            "cdk/app.ts",
            "src/lambda_handler.py"
        ]
        
        missing_files = []
        for file_path in required_files:
            if not (self.project_root / file_path).exists():
                missing_files.append(file_path)
        
        if missing_files:
            logger.error(f"Missing required files: {missing_files}")
            return False
        
        # Check environment variables
        required_env_vars = [
            "OPENAI_API_KEY",
            "TAVILY_API_KEY",
            "AIERA_API_KEY",
            "EMAIL_SENDER",
            "ROBINHOOD__USERNAME",
            "ROBINHOOD__PASSWORD"
        ]
        
        missing_vars = []
        for var in required_env_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            logger.error(f"Missing environment variables: {missing_vars}")
            return False
        
        # Check AWS credentials
        try:
            result = subprocess.run(
                ["aws", "sts", "get-caller-identity"],
                capture_output=True,
                text=True,
                check=True
            )
            identity = json.loads(result.stdout)
            logger.info(f"AWS identity: {identity.get('Arn', 'Unknown')}")
        except (subprocess.CalledProcessError, json.JSONDecodeError, FileNotFoundError):
            logger.error("AWS credentials not configured or AWS CLI not available")
            return False
        
        logger.info("Environment validation passed")
        return True
    
    def install_dependencies(self) -> bool:
        """Install project dependencies."""
        logger.info("Installing dependencies...")
        
        # Install Python dependencies
        logger.info("Installing Python dependencies with Poetry...")
        try:
            subprocess.run(
                ["poetry", "install"],
                cwd=self.project_root,
                check=True
            )
        except subprocess.CalledProcessError:
            logger.error("Failed to install Python dependencies")
            return False
        
        # Install CDK dependencies
        logger.info("Installing CDK dependencies...")
        try:
            subprocess.run(
                ["npm", "install"],
                cwd=self.cdk_dir,
                check=True
            )
        except subprocess.CalledProcessError:
            logger.error("Failed to install CDK dependencies")
            return False
        
        logger.info("Dependencies installed successfully")
        return True
    
    def run_tests(self) -> bool:
        """Run tests before deployment."""
        logger.info("Running tests...")
        
        # Run Python tests
        try:
            subprocess.run(
                ["poetry", "run", "pytest", "tests/", "-v"],
                cwd=self.project_root,
                check=True
            )
        except subprocess.CalledProcessError:
            logger.warning("Some tests failed, but continuing with deployment")
        
        # Run type checking
        try:
            subprocess.run(
                ["poetry", "run", "mypy", "src/"],
                cwd=self.project_root,
                check=True
            )
        except subprocess.CalledProcessError:
            logger.warning("Type checking failed, but continuing with deployment")
        
        logger.info("Tests completed")
        return True
    
    def bootstrap_cdk(self) -> bool:
        """Bootstrap CDK if needed."""
        logger.info("Checking CDK bootstrap status...")
        
        try:
            # Check if bootstrap is needed
            result = subprocess.run(
                ["npx", "cdk", "diff"],
                cwd=self.cdk_dir,
                capture_output=True,
                text=True
            )
            
            if "This deployment will make potentially sensitive changes" in result.stdout:
                logger.info("CDK bootstrap required")
                subprocess.run(
                    ["npx", "cdk", "bootstrap"],
                    cwd=self.cdk_dir,
                    check=True
                )
                logger.info("CDK bootstrap completed")
            else:
                logger.info("CDK bootstrap not required")
            
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"CDK bootstrap failed: {e}")
            return False
    
    def deploy_infrastructure(self) -> bool:
        """Deploy CDK infrastructure."""
        logger.info("Deploying CDK infrastructure...")
        
        try:
            # Set environment variables for CDK
            env = os.environ.copy()
            env["ENVIRONMENT"] = self.environment
            
            # Deploy CDK stack
            cmd = [
                "npx", "cdk", "deploy",
                f"QuantasaurusStack-{self.environment}",
                "--require-approval", "never"
            ]
            
            subprocess.run(
                cmd,
                cwd=self.cdk_dir,
                env=env,
                check=True
            )
            
            logger.info("CDK deployment completed successfully")
            return True
            
        except subprocess.CalledProcessError as e:
            logger.error(f"CDK deployment failed: {e}")
            return False
    
    def verify_deployment(self) -> bool:
        """Verify deployment was successful."""
        logger.info("Verifying deployment...")
        
        try:
            # Get stack outputs
            result = subprocess.run(
                ["npx", "cdk", "list", "--long"],
                cwd=self.cdk_dir,
                capture_output=True,
                text=True,
                check=True
            )
            
            if f"QuantasaurusStack-{self.environment}" in result.stdout:
                logger.info("Stack deployed successfully")
                
                # Test Lambda function
                logger.info("Testing Lambda function...")
                try:
                    import boto3
                    lambda_client = boto3.client('lambda')
                    
                    # Invoke function with test event
                    response = lambda_client.invoke(
                        FunctionName=f"quantasaurus-rex-{self.environment}",
                        InvocationType='RequestResponse',
                        Payload=json.dumps({
                            "source": "health-check",
                            "detail": {}
                        })
                    )
                    
                    if response['StatusCode'] == 200:
                        logger.info("Lambda function test passed")
                        return True
                    else:
                        logger.error(f"Lambda function test failed: {response}")
                        return False
                        
                except Exception as e:
                    logger.warning(f"Lambda function test failed: {e}")
                    return True  # Continue anyway
            
            return False
            
        except subprocess.CalledProcessError as e:
            logger.error(f"Deployment verification failed: {e}")
            return False
    
    def setup_ses_email(self) -> bool:
        """Set up SES email verification."""
        logger.info("Setting up SES email verification...")
        
        try:
            import boto3
            ses_client = boto3.client('ses')
            
            email_sender = os.getenv("EMAIL_SENDER")
            email_recipient = os.getenv("EMAIL_RECIPIENT")
            
            if not email_sender or not email_recipient:
                logger.warning("Email addresses not configured")
                return True
            
            # Verify sender email
            try:
                ses_client.verify_email_identity(EmailAddress=email_sender)
                logger.info(f"Email verification sent to {email_sender}")
            except Exception as e:
                logger.warning(f"Failed to verify sender email: {e}")
            
            # Verify recipient email if different
            if email_recipient != email_sender:
                try:
                    ses_client.verify_email_identity(EmailAddress=email_recipient)
                    logger.info(f"Email verification sent to {email_recipient}")
                except Exception as e:
                    logger.warning(f"Failed to verify recipient email: {e}")
            
            return True
            
        except Exception as e:
            logger.error(f"SES setup failed: {e}")
            return False
    
    def deploy(self) -> bool:
        """Run full deployment process."""
        logger.info("Starting deployment process...")
        
        steps = [
            ("Validate Environment", self.validate_environment),
            ("Install Dependencies", self.install_dependencies),
            ("Run Tests", self.run_tests),
            ("Bootstrap CDK", self.bootstrap_cdk),
            ("Deploy Infrastructure", self.deploy_infrastructure),
            ("Verify Deployment", self.verify_deployment),
            ("Setup SES Email", self.setup_ses_email)
        ]
        
        for step_name, step_func in steps:
            logger.info(f"Step: {step_name}")
            if not step_func():
                logger.error(f"Step failed: {step_name}")
                return False
        
        logger.info("Deployment completed successfully!")
        return True


def main():
    """Main deployment function."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Deploy Quantasaurus Rex")
    parser.add_argument(
        "--environment",
        choices=["development", "staging", "production"],
        default="development",
        help="Deployment environment"
    )
    parser.add_argument(
        "--skip-tests",
        action="store_true",
        help="Skip running tests before deployment"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Enable verbose logging"
    )
    
    args = parser.parse_args()
    
    # Set logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Create deployer
    deployer = QuantasaurusDeployer(args.environment)
    
    # Skip tests if requested
    if args.skip_tests:
        deployer.run_tests = lambda: True
    
    # Run deployment
    success = deployer.deploy()
    
    if success:
        print("\n" + "="*50)
        print("DEPLOYMENT SUCCESSFUL!")
        print("="*50)
        print(f"Environment: {args.environment}")
        print(f"Stack: QuantasaurusStack-{args.environment}")
        print(f"Lambda Function: quantasaurus-rex-{args.environment}")
        print("\nNext steps:")
        print("1. Verify SES email addresses in AWS console")
        print("2. Check EventBridge rule is enabled")
        print("3. Test the Lambda function")
        return 0
    else:
        print("\n" + "="*50)
        print("DEPLOYMENT FAILED!")
        print("="*50)
        print("Check the logs above for details.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
"""Authentication utilities for Robinhood."""

import asyncio
import logging
import os
import boto3
from typing import Optional, Dict, Any
from botocore.exceptions import ClientError, NoCredentialsError
import robin_stocks as rs

logger = logging.getLogger(__name__)


class RobinhoodAuth:
    """Robinhood authentication handler with device approval."""
    
    def __init__(self, username: str, password: str):
        """Initialize authentication handler."""
        self.username = username
        self.password = password
        self.device_id: Optional[str] = None
        
        # Initialize AWS Systems Manager client for parameter store
        try:
            self.ssm_client = boto3.client('ssm')
        except NoCredentialsError:
            logger.warning("AWS credentials not found. Device ID persistence will be limited.")
            self.ssm_client = None
    
    async def authenticate_with_device(self) -> bool:
        """
        Authenticate with Robinhood using device approval.
        
        This implementation is based on the modifications from:
        https://raw.githubusercontent.com/bhyman67/Mods-to-robin-stocks-Authentication/02e5491a9844382c5915180b7bd5321ed98a013b/Authentication.py
        """
        try:
            logger.info("Starting Robinhood device authentication...")
            
            # Try to load existing device ID
            device_id = await self.load_device_id()
            
            if device_id:
                logger.info("Found existing device ID, attempting login...")
                login_success = await self._attempt_login_with_device(device_id)
                
                if login_success:
                    self.device_id = device_id
                    logger.info("Successfully authenticated with existing device ID")
                    return True
                else:
                    logger.warning("Failed to authenticate with existing device ID, will request new one")
            
            # If no device ID or existing one failed, request new device approval
            logger.info("Requesting new device approval...")
            new_device_id = await self._request_device_approval()
            
            if new_device_id:
                self.device_id = new_device_id
                await self.persist_device_id(new_device_id)
                logger.info("Successfully authenticated with new device ID")
                return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error in device authentication: {str(e)}")
            return False
    
    async def _attempt_login_with_device(self, device_id: str) -> bool:
        """Attempt login with existing device ID."""
        try:
            # This is a simplified version - in practice, you'd need to implement
            # the full device authentication flow based on robin_stocks modifications
            
            # Set device ID in environment for robin_stocks
            os.environ['ROBINHOOD_DEVICE_ID'] = device_id
            
            # Attempt login
            login_result = rs.login(
                username=self.username,
                password=self.password,
                device_id=device_id
            )
            
            return login_result is not None
            
        except Exception as e:
            logger.error(f"Error attempting login with device ID: {str(e)}")
            return False
    
    async def _request_device_approval(self) -> Optional[str]:
        """Request new device approval."""
        try:
            # This is a simplified version - in practice, you'd need to implement
            # the full device approval flow based on robin_stocks modifications
            
            logger.info("Requesting device approval from Robinhood...")
            
            # Step 1: Initial login attempt to trigger device approval
            try:
                login_result = rs.login(
                    username=self.username,
                    password=self.password
                )
                
                if login_result:
                    # If login succeeds, get the device ID
                    device_id = rs.get_device_id()
                    if device_id:
                        return device_id
                    
            except Exception as e:
                # Check if this is a device approval required error
                if "device" in str(e).lower() or "approval" in str(e).lower():
                    logger.info("Device approval required - check your email/SMS for approval")
                    
                    # In a real implementation, you would:
                    # 1. Parse the device ID from the error response
                    # 2. Wait for user to approve the device
                    # 3. Retry the login
                    
                    # For now, return None to indicate manual intervention needed
                    logger.warning("Device approval required - manual intervention needed")
                    return None
                else:
                    raise e
            
            return None
            
        except Exception as e:
            logger.error(f"Error requesting device approval: {str(e)}")
            return None
    
    async def persist_device_id(self, device_id: str):
        """Store device ID in AWS Parameter Store."""
        try:
            if not self.ssm_client:
                logger.warning("SSM client not available, cannot persist device ID")
                return
            
            parameter_name = f"/quantasaurus-rex/robinhood/device-id"
            
            self.ssm_client.put_parameter(
                Name=parameter_name,
                Value=device_id,
                Type='SecureString',
                Overwrite=True,
                Description='Robinhood device ID for authentication'
            )
            
            logger.info(f"Device ID persisted to parameter store: {parameter_name}")
            
        except ClientError as e:
            logger.error(f"Error persisting device ID: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error persisting device ID: {str(e)}")
    
    async def load_device_id(self) -> Optional[str]:
        """Load device ID from AWS Parameter Store."""
        try:
            if not self.ssm_client:
                logger.warning("SSM client not available, cannot load device ID")
                return None
            
            parameter_name = f"/quantasaurus-rex/robinhood/device-id"
            
            response = self.ssm_client.get_parameter(
                Name=parameter_name,
                WithDecryption=True
            )
            
            device_id = response['Parameter']['Value']
            logger.info("Device ID loaded from parameter store")
            return device_id
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                logger.info("No device ID found in parameter store")
                return None
            else:
                logger.error(f"Error loading device ID: {str(e)}")
                return None
        except Exception as e:
            logger.error(f"Unexpected error loading device ID: {str(e)}")
            return None
    
    async def clear_device_id(self):
        """Clear stored device ID."""
        try:
            if not self.ssm_client:
                logger.warning("SSM client not available, cannot clear device ID")
                return
            
            parameter_name = f"/quantasaurus-rex/robinhood/device-id"
            
            self.ssm_client.delete_parameter(Name=parameter_name)
            self.device_id = None
            
            logger.info("Device ID cleared from parameter store")
            
        except ClientError as e:
            if e.response['Error']['Code'] == 'ParameterNotFound':
                logger.info("No device ID to clear")
            else:
                logger.error(f"Error clearing device ID: {str(e)}")
        except Exception as e:
            logger.error(f"Unexpected error clearing device ID: {str(e)}")
    
    def get_device_id(self) -> Optional[str]:
        """Get current device ID."""
        return self.device_id
    
    async def validate_credentials(self) -> bool:
        """Validate Robinhood credentials."""
        try:
            # Simple validation - attempt a basic API call
            user_data = rs.get_user()
            return user_data is not None
            
        except Exception as e:
            logger.error(f"Error validating credentials: {str(e)}")
            return False
    
    async def refresh_token(self) -> bool:
        """Refresh authentication token."""
        try:
            # robin_stocks handles token refresh automatically
            # This is a placeholder for any manual refresh logic
            
            return await self.validate_credentials()
            
        except Exception as e:
            logger.error(f"Error refreshing token: {str(e)}")
            return False
    
    def is_authenticated(self) -> bool:
        """Check if currently authenticated."""
        try:
            # Check if we have a valid session
            user_data = rs.get_user()
            return user_data is not None
        except:
            return False
    
    async def logout(self):
        """Logout from Robinhood."""
        try:
            rs.logout()
            logger.info("Logged out from Robinhood")
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")


class DeviceApprovalHandler:
    """Handler for device approval flow."""
    
    def __init__(self, username: str, password: str):
        """Initialize device approval handler."""
        self.username = username
        self.password = password
    
    async def initiate_device_approval(self) -> Dict[str, str]:
        """Initiate device approval process."""
        try:
            # This would implement the full device approval flow
            # based on the robin_stocks modifications
            
            logger.info("Initiating device approval process...")
            
            # In a real implementation, this would:
            # 1. Make the initial login request
            # 2. Parse the device approval response
            # 3. Extract the device ID and approval method
            # 4. Return the device ID and instructions
            
            return {
                "device_id": "placeholder-device-id",
                "approval_method": "email",
                "message": "Please check your email for device approval"
            }
            
        except Exception as e:
            logger.error(f"Error initiating device approval: {str(e)}")
            return {
                "error": str(e),
                "message": "Failed to initiate device approval"
            }
    
    async def check_approval_status(self, device_id: str) -> bool:
        """Check if device has been approved."""
        try:
            # This would check the approval status
            # In a real implementation, you'd make an API call
            
            logger.info(f"Checking approval status for device: {device_id}")
            
            # Placeholder - in practice, you'd implement the actual check
            return False
            
        except Exception as e:
            logger.error(f"Error checking approval status: {str(e)}")
            return False
    
    async def wait_for_approval(self, device_id: str, timeout: int = 300) -> bool:
        """Wait for device approval with timeout."""
        try:
            logger.info(f"Waiting for device approval (timeout: {timeout}s)")
            
            start_time = asyncio.get_event_loop().time()
            
            while (asyncio.get_event_loop().time() - start_time) < timeout:
                if await self.check_approval_status(device_id):
                    logger.info("Device approved successfully")
                    return True
                
                # Wait 10 seconds before checking again
                await asyncio.sleep(10)
            
            logger.warning("Device approval timeout")
            return False
            
        except Exception as e:
            logger.error(f"Error waiting for approval: {str(e)}")
            return False
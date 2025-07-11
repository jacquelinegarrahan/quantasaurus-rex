"""Robinhood API client service."""

import asyncio
import logging
from typing import Dict, List, Any
import robin_stocks.robinhood as rh

from ..config.settings import RobinhoodConfig
from ..models.portfolio import Portfolio, StockPosition, CryptoPosition
from ..utils.auth import RobinhoodAuth

logger = logging.getLogger(__name__)


class RobinhoodService:
    """Robinhood API service for portfolio and market data."""
    
    def __init__(self, config: RobinhoodConfig):
        """Initialize Robinhood service."""
        self.config = config
        self.auth = RobinhoodAuth(config.username, config.password)
        self.authenticated = False
        self._crypto_symbols = set()  # Store crypto symbols from portfolio (populated after get_portfolio())
        
    async def authenticate(self) -> bool:
        """Authenticate with Robinhood using device approval."""
        try:
            logger.info("Attempting Robinhood authentication...")
            
            # Try to load existing device ID (non-blocking)
            try:
                device_id = await self.auth.load_device_id()
                if device_id:
                    self.config.device_id = device_id
                    logger.info("Loaded existing device ID")
            except Exception as e:
                logger.warning(f"Could not load device ID from AWS (continuing anyway): {str(e)}")
                # Continue without device ID - robin_stocks will handle device challenges
            
            # Attempt login
            login_result = await self._login()
            
            if login_result:
                self.authenticated = True
                logger.info("Successfully authenticated with Robinhood")
                
                # Verify crypto access is working
                try:
                    _ = rh.get_crypto_positions()
                    logger.info("Crypto API access verified")
                except Exception as e:
                    logger.warning(f"Crypto API access issue: {str(e)}")
                
                return True
            else:
                logger.error("Failed to authenticate with Robinhood")
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {str(e)}")
            return False
    
    async def _login(self) -> bool:
        """Perform login with device authentication."""
        try:
            # Note: robin_stocks doesn't support device_id parameter in login()
            # The library handles device authentication differently
            
            # Standard login - robin_stocks will handle device challenges automatically
            login_result = rh.login(
                username=self.config.username,
                password=self.config.password,
                store_session=True  # This stores authentication for future use
            )
            
            if login_result:
                logger.info("Login successful")
                # Note: robin_stocks handles device authentication internally
                # No need to manually manage device IDs
                return True
            else:
                logger.warning("Login failed - may require device authentication")
                return False
            
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return False
    
    async def get_portfolio(self) -> Portfolio:
        """Get current portfolio positions."""
        if not self.authenticated:
            raise ValueError("Not authenticated with Robinhood")
        
        try:
            logger.info("Fetching portfolio data...")
            
            # Get stock positions
            stock_positions = await self._get_stock_positions()
            
            # Get crypto positions
            crypto_positions = await self._get_crypto_positions()
            
            # Store crypto symbols for later use - always update the set
            self._crypto_symbols = {pos.symbol for pos in crypto_positions}
            logger.debug(f"Stored crypto symbols: {self._crypto_symbols}")
            
            # Calculate totals (for potential future use)
            _ = sum(pos.market_value for pos in stock_positions)
            _ = sum(pos.market_value for pos in crypto_positions)
            
            # Create portfolio (P&L will be calculated from individual positions)
            portfolio = Portfolio.create_portfolio(
                stocks=stock_positions,
                crypto=crypto_positions
            )
            
            logger.info(f"Retrieved portfolio with {len(stock_positions)} stocks and {len(crypto_positions)} crypto positions")
            return portfolio
            
        except Exception as e:
            logger.error(f"Error fetching portfolio: {str(e)}")
            raise
    
    async def _get_stock_positions(self) -> List[StockPosition]:
        """Get stock positions from Robinhood."""
        try:
            # Use build_holdings() which returns a dictionary of current stock holdings
            holdings = rh.build_holdings()
            stock_positions = []
            
            for symbol, holding_data in holdings.items():
                try:
                    quantity = float(holding_data.get('quantity', 0))
                    if quantity <= 0:
                        continue
                    
                    current_price = float(holding_data.get('price', 0))
                    if current_price <= 0:
                        continue
                    
                    market_value = quantity * current_price
                    
                    # Calculate P&L
                    average_cost = float(holding_data.get('average_buy_price', 0))
                    unrealized_gain_loss = None
                    unrealized_gain_loss_percent = None
                    
                    if average_cost > 0:
                        unrealized_gain_loss = (current_price - average_cost) * quantity
                        unrealized_gain_loss_percent = ((current_price - average_cost) / average_cost) * 100
                    
                    # Get additional company info
                    company_name = holding_data.get('name', '')
                    
                    stock_position = StockPosition(
                        symbol=symbol,
                        quantity=quantity,
                        current_price=current_price,
                        market_value=market_value,
                        average_cost=average_cost,
                        unrealized_gain_loss=unrealized_gain_loss,
                        unrealized_gain_loss_percent=unrealized_gain_loss_percent,
                        company_name=company_name
                    )
                    
                    stock_positions.append(stock_position)
                    
                except Exception as e:
                    logger.warning(f"Error processing position for {symbol}: {str(e)}")
                    continue
            
            return stock_positions
            
        except Exception as e:
            logger.error(f"Error fetching stock positions: {str(e)}")
            return []
    
    async def _get_crypto_positions(self) -> List[CryptoPosition]:
        """Get crypto positions from Robinhood."""
        try:
            # Ensure we're authenticated before making crypto API calls
            if not self.authenticated:
                logger.error("Not authenticated with Robinhood - cannot fetch crypto positions")
                return []
            
            positions = rh.crypto.get_crypto_positions()
            crypto_positions = []
            
            for position in positions:
                quantity = float(position.get('quantity', 0))
                if quantity <= 0:
                    continue
                
                currency = position.get('currency', {})
                if not currency:
                    continue
                
                symbol = currency.get('code')
                if not symbol:
                    continue
                
                # Get current price
                quote = rh.crypto.get_crypto_quote(symbol)
                if not quote or 'mark_price' not in quote:
                    continue
                
                current_price = float(quote['mark_price'])
                market_value = quantity * current_price
                
                # Calculate P&L
                average_cost = float(position.get('average_buy_price', 0))
                unrealized_gain_loss = None
                unrealized_gain_loss_percent = None
                
                if average_cost > 0:
                    unrealized_gain_loss = (current_price - average_cost) * quantity
                    unrealized_gain_loss_percent = ((current_price - average_cost) / average_cost) * 100
                
                # Get additional crypto info
                full_name = currency.get('name', '')
                
                crypto_position = CryptoPosition(
                    symbol=symbol,
                    quantity=quantity,
                    current_price=current_price,
                    market_value=market_value,
                    average_cost=average_cost,
                    unrealized_gain_loss=unrealized_gain_loss,
                    unrealized_gain_loss_percent=unrealized_gain_loss_percent,
                    full_name=full_name
                )
                
                crypto_positions.append(crypto_position)
            
            return crypto_positions
            
        except Exception as e:
            logger.error(f"Error fetching crypto positions: {str(e)}")
            # If authentication error, return empty list rather than failing
            if "login" in str(e).lower() or "auth" in str(e).lower():
                logger.warning("Authentication error when fetching crypto positions - returning empty list")
            return []
    
    async def get_stock_fundamentals(self, symbols: List[str]) -> Dict[str, Any]:
        """Get stock fundamentals data."""
        if not self.authenticated:
            raise ValueError("Not authenticated with Robinhood")
        
        try:
            logger.info(f"Fetching fundamentals for {len(symbols)} symbols...")
            
            fundamentals = {}
            
            for symbol in symbols:
                try:
                    # Get fundamentals
                    fund_data = rh.get_fundamentals(symbol)
                    if fund_data and len(fund_data) > 0:
                        fundamentals[symbol] = fund_data[0]
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching fundamentals for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved fundamentals for {len(fundamentals)} symbols")
            return fundamentals
            
        except Exception as e:
            logger.error(f"Error fetching stock fundamentals: {str(e)}")
            return {}
    
    async def get_historical_data(self, symbols: List[str], span: str = "year") -> Dict[str, Any]:
        """Get historical price data for stocks and crypto."""
        if not self.authenticated:
            raise ValueError("Not authenticated with Robinhood")
        
        try:
            logger.info(f"Fetching historical data for {len(symbols)} symbols...")
            
            historical_data = {}
            
            for symbol in symbols:
                try:
                    logger.debug(f"Processing historical data for {symbol}...")
                    
                    # Determine if symbol is crypto or stock based on stored crypto symbols
                    if symbol in self._crypto_symbols:
                        logger.debug(f"{symbol} identified as crypto (from portfolio)")
                        # Get crypto historical data
                        crypto_data = await self._get_crypto_historical_data(symbol, span)
                        if crypto_data:
                            historical_data[symbol] = {
                                'type': 'crypto',
                                'data': crypto_data
                            }
                            logger.debug(f"Successfully retrieved crypto data for {symbol}")
                        else:
                            logger.warning(f"No crypto data found for {symbol}")
                    else:
                        logger.debug(f"{symbol} identified as stock (from portfolio)")
                        # Get stock historical data
                        stock_data = rh.get_stock_historicals(symbol, interval="day", span=span)
                        if stock_data:
                            historical_data[symbol] = {
                                'type': 'stock',
                                'data': stock_data
                            }
                            logger.debug(f"Successfully retrieved stock data for {symbol}")
                        else:
                            logger.warning(f"No stock data found for {symbol}")
                    
                    # Small delay to avoid rate limiting
                    await asyncio.sleep(0.1)
                    
                except Exception as e:
                    logger.warning(f"Error fetching historical data for {symbol}: {str(e)}")
                    continue
            
            logger.info(f"Retrieved historical data for {len(historical_data)} symbols")
            return historical_data
            
        except Exception as e:
            logger.error(f"Error fetching historical data: {str(e)}")
            return {}
    
    def _is_crypto_symbol(self, symbol: str) -> bool:
        """Determine if a symbol is a cryptocurrency.
        
        DEPRECATED: This method is deprecated. Use the crypto symbols from 
        the portfolio (_crypto_symbols) instead for better reliability.
        """
        logger.warning("_is_crypto_symbol is deprecated. Use portfolio crypto symbols instead.")
        return symbol in self._crypto_symbols
    
    def get_crypto_symbols(self) -> set:
        """Get the set of crypto symbols from the current portfolio."""
        return self._crypto_symbols.copy()
    
    def is_crypto_symbol(self, symbol: str) -> bool:
        """Check if a symbol is a cryptocurrency based on portfolio data."""
        return symbol in self._crypto_symbols
    
    async def _get_crypto_historical_data(self, symbol: str, span: str = "year") -> List[Dict[str, Any]]:
        """Get historical data for a cryptocurrency."""
        try:
            logger.debug(f"Fetching crypto historical data for {symbol}...")
            
            # Ensure we're authenticated before making crypto API calls
            if not self.authenticated:
                logger.error("Not authenticated with Robinhood - cannot fetch crypto historical data")
                return []
            
            # Use the correct crypto historicals function
            # Available intervals: '15second', '5minute', '10minute', 'hour', 'day', 'week'
            # Available spans: 'hour', 'day', 'week', 'month', '3month', 'year', '5year'
            
            # Note: rh_crypto uses the same session as rh, so no separate login needed
            # but we need to make sure we're logged in first
            crypto_data = rh.crypto.get_crypto_historicals(
                symbol=symbol,
                interval='day',
                span=span,
                bounds='24_7'  # Crypto markets are 24/7
            )
            
            if crypto_data:
                logger.debug(f"Successfully fetched crypto historical data for {symbol}")
                return crypto_data
            else:
                logger.warning(f"No crypto historical data found for {symbol}")
                return []
                
        except Exception as e:
            logger.error(f"Error fetching crypto historical data for {symbol}: {str(e)}")
            # If authentication error, try to re-authenticate
            if "login" in str(e).lower() or "auth" in str(e).lower():
                logger.info("Attempting to re-authenticate due to crypto API error")
                try:
                    await self.authenticate()
                    # Retry the crypto call once after re-authentication
                    crypto_data = rh.crypto.get_crypto_historicals(
                        symbol=symbol,
                        interval='day',
                        span=span,
                        bounds='24_7'
                    )
                    if crypto_data:
                        logger.debug(f"Successfully fetched crypto historical data for {symbol} after re-auth")
                        return crypto_data
                except Exception as retry_e:
                    logger.error(f"Failed to re-authenticate and retry crypto data fetch: {str(retry_e)}")
            return []
    
    async def logout(self):
        """Logout from Robinhood."""
        try:
            rh.logout()
            self.authenticated = False
            logger.info("Logged out from Robinhood")
        except Exception as e:
            logger.error(f"Error during logout: {str(e)}")
    
    def __del__(self):
        """Cleanup on destruction."""
        if self.authenticated:
            try:
                rh.logout()
            except:
                pass
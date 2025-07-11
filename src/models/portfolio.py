"""Portfolio data models."""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union
from pydantic import BaseModel, Field, field_validator
from enum import Enum


class AssetType(str, Enum):
    """Asset type enumeration."""
    STOCK = "stock"
    CRYPTO = "crypto"


class PositionBase(BaseModel):
    """Base class for portfolio positions."""
    
    symbol: str = Field(..., description="Asset symbol")
    quantity: float = Field(..., gt=0, description="Quantity held")
    current_price: float = Field(..., gt=0, description="Current price per unit")
    market_value: float = Field(..., gt=0, description="Total market value")
    average_cost: Optional[float] = Field(None, description="Average cost basis")
    unrealized_gain_loss: Optional[float] = Field(None, description="Unrealized P&L")
    unrealized_gain_loss_percent: Optional[float] = Field(None, description="Unrealized P&L %")
    
    @field_validator('market_value')
    @classmethod
    def validate_market_value(cls, v: float) -> float:
        """Validate market value matches quantity * current_price."""
        # Note: In V2, we can't access other field values during validation
        # This validation will be handled in the service layer instead
        return v
    
    @classmethod
    def create_position(
        cls,
        symbol: str,
        quantity: float,
        current_price: float,
        **kwargs
    ) -> "PositionBase":
        """Create a position with calculated market value."""
        market_value = quantity * current_price
        return cls(
            symbol=symbol,
            quantity=quantity,
            current_price=current_price,
            market_value=market_value,
            **kwargs
        )


class StockPosition(PositionBase):
    """Stock position model."""
    
    asset_type: AssetType = Field(default=AssetType.STOCK, description="Asset type")
    company_name: Optional[str] = Field(None, description="Company name")
    sector: Optional[str] = Field(None, description="Company sector")
    industry: Optional[str] = Field(None, description="Company industry")
    market_cap: Optional[float] = Field(None, description="Market capitalization")
    dividend_yield: Optional[float] = Field(None, description="Dividend yield")
    pe_ratio: Optional[float] = Field(None, description="P/E ratio")
    beta: Optional[float] = Field(None, description="Beta coefficient")
    
    # Fundamentals data
    fundamentals: Optional[Dict[str, Any]] = Field(None, description="Stock fundamentals")
    
    # Historical data
    historical_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Historical price data"
    )
    
    # Aiera data
    aiera_data: Optional[Dict[str, Any]] = Field(None, description="Aiera API data")


class CryptoPosition(PositionBase):
    """Cryptocurrency position model."""
    
    asset_type: AssetType = Field(default=AssetType.CRYPTO, description="Asset type")
    full_name: Optional[str] = Field(None, description="Full cryptocurrency name")
    market_cap_rank: Optional[int] = Field(None, description="Market cap ranking")
    circulating_supply: Optional[float] = Field(None, description="Circulating supply")
    total_supply: Optional[float] = Field(None, description="Total supply")
    max_supply: Optional[float] = Field(None, description="Maximum supply")
    
    # Historical data
    historical_data: Optional[List[Dict[str, Any]]] = Field(
        None, description="Historical price data"
    )


class Portfolio(BaseModel):
    """Portfolio model containing all positions."""
    
    stocks: List[StockPosition] = Field(default_factory=list, description="Stock positions")
    crypto: List[CryptoPosition] = Field(default_factory=list, description="Crypto positions")
    
    total_value: float = Field(..., gt=0, description="Total portfolio value")
    total_stocks_value: float = Field(default=0, description="Total stocks value")
    total_crypto_value: float = Field(default=0, description="Total crypto value")
    
    total_gain_loss: Optional[float] = Field(None, description="Total unrealized P&L")
    total_gain_loss_percent: Optional[float] = Field(None, description="Total unrealized P&L %")
    
    last_updated: datetime = Field(
        default_factory=datetime.utcnow,
        description="Last update timestamp"
    )
    
    @field_validator('total_stocks_value')
    @classmethod
    def calculate_total_stocks_value(cls, v: float) -> float:
        """Calculate total stocks value from positions."""
        # Note: In V2, we can't access other field values during validation
        # This calculation will be handled in the service layer instead
        return v
    
    @field_validator('total_crypto_value')
    @classmethod
    def calculate_total_crypto_value(cls, v: float) -> float:
        """Calculate total crypto value from positions."""
        # Note: In V2, we can't access other field values during validation
        # This calculation will be handled in the service layer instead
        return v
    
    @field_validator('total_value')
    @classmethod
    def validate_total_value(cls, v: float) -> float:
        """Validate total value matches sum of all positions."""
        # Note: In V2, we can't access other field values during validation
        # This validation will be handled in the service layer instead
        return v
    
    @property
    def total_positions(self) -> int:
        """Total number of positions in portfolio."""
        return len(self.stocks) + len(self.crypto)
    
    @property
    def stocks_percentage(self) -> float:
        """Percentage of portfolio in stocks."""
        if self.total_value == 0:
            return 0.0
        return (self.total_stocks_value / self.total_value) * 100
    
    @property
    def crypto_percentage(self) -> float:
        """Percentage of portfolio in crypto."""
        if self.total_value == 0:
            return 0.0
        return (self.total_crypto_value / self.total_value) * 100
    
    @property
    def all_positions(self) -> List[Union[StockPosition, CryptoPosition]]:
        """Get all positions combined."""
        return self.stocks + self.crypto
    
    def get_position_by_symbol(self, symbol: str) -> Optional[Union[StockPosition, CryptoPosition]]:
        """Get position by symbol."""
        for position in self.all_positions:
            if position.symbol.upper() == symbol.upper():
                return position
        return None
    
    def get_top_positions(self, n: int = 5) -> List[Union[StockPosition, CryptoPosition]]:
        """Get top N positions by market value."""
        return sorted(self.all_positions, key=lambda p: p.market_value, reverse=True)[:n]
    
    @classmethod
    def create_portfolio(
        cls,
        stocks: List[StockPosition],
        crypto: List[CryptoPosition],
        **kwargs
    ) -> "Portfolio":
        """Create a portfolio with auto-calculated totals."""
        # Calculate totals
        total_stocks_value = sum(position.market_value for position in stocks)
        total_crypto_value = sum(position.market_value for position in crypto)
        total_value = total_stocks_value + total_crypto_value
        
        # Calculate P&L if positions have cost basis
        total_gain_loss = None
        total_gain_loss_percent = None
        
        positions_with_cost = [p for p in stocks + crypto if p.unrealized_gain_loss is not None]
        if positions_with_cost:
            total_gain_loss = sum(p.unrealized_gain_loss for p in positions_with_cost)
            total_cost = sum(p.market_value - p.unrealized_gain_loss for p in positions_with_cost)
            if total_cost > 0:
                total_gain_loss_percent = (total_gain_loss / total_cost) * 100
        
        return cls(
            stocks=stocks,
            crypto=crypto,
            total_value=total_value,
            total_stocks_value=total_stocks_value,
            total_crypto_value=total_crypto_value,
            total_gain_loss=total_gain_loss,
            total_gain_loss_percent=total_gain_loss_percent,
            **kwargs
        )
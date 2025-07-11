"""Data processing utilities for Quantasaurus Rex."""

import logging
import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
import statistics

logger = logging.getLogger(__name__)


class DataProcessor:
    """Utility class for data processing and analysis."""
    
    @staticmethod
    def calculate_technical_indicators(price_data: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate technical indicators from price data."""
        try:
            if not price_data or len(price_data) < 2:
                return {}
            
            # Extract price information
            closes = [float(item.get('close', 0)) for item in price_data if item.get('close')]
            highs = [float(item.get('high', 0)) for item in price_data if item.get('high')]
            lows = [float(item.get('low', 0)) for item in price_data if item.get('low')]
            volumes = [float(item.get('volume', 0)) for item in price_data if item.get('volume')]
            
            if not closes:
                return {}
            
            indicators = {}
            
            # Simple Moving Averages
            if len(closes) >= 20:
                indicators['sma_20'] = statistics.mean(closes[-20:])
            if len(closes) >= 50:
                indicators['sma_50'] = statistics.mean(closes[-50:])
            if len(closes) >= 200:
                indicators['sma_200'] = statistics.mean(closes[-200:])
            
            # RSI (Relative Strength Index)
            if len(closes) >= 14:
                indicators['rsi'] = DataProcessor._calculate_rsi(closes)
            
            # MACD
            if len(closes) >= 26:
                macd_data = DataProcessor._calculate_macd(closes)
                indicators.update(macd_data)
            
            # Bollinger Bands
            if len(closes) >= 20:
                bb_data = DataProcessor._calculate_bollinger_bands(closes)
                indicators.update(bb_data)
            
            # Volatility
            if len(closes) >= 2:
                indicators['volatility'] = DataProcessor._calculate_volatility(closes)
            
            # Support and Resistance
            if len(closes) >= 20:
                support, resistance = DataProcessor._calculate_support_resistance(closes, highs, lows)
                indicators['support_level'] = support
                indicators['resistance_level'] = resistance
            
            # Volume indicators
            if volumes and len(volumes) >= 10:
                indicators['volume_avg'] = statistics.mean(volumes[-10:])
                if len(volumes) >= 2:
                    indicators['volume_ratio'] = volumes[-1] / statistics.mean(volumes[-10:]) if statistics.mean(volumes[-10:]) > 0 else 1
            
            return indicators
            
        except Exception as e:
            logger.error(f"Error calculating technical indicators: {str(e)}")
            return {}
    
    @staticmethod
    def _calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Calculate Relative Strength Index."""
        try:
            if len(prices) < period + 1:
                return 50.0  # Neutral RSI
            
            # Calculate price changes
            changes = [prices[i] - prices[i-1] for i in range(1, len(prices))]
            
            # Separate gains and losses
            gains = [change if change > 0 else 0 for change in changes]
            losses = [-change if change < 0 else 0 for change in changes]
            
            # Calculate average gain and loss
            avg_gain = statistics.mean(gains[-period:])
            avg_loss = statistics.mean(losses[-period:])
            
            # Calculate RSI
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            return round(rsi, 2)
            
        except Exception as e:
            logger.error(f"Error calculating RSI: {str(e)}")
            return 50.0
    
    @staticmethod
    def _calculate_macd(prices: List[float]) -> Dict[str, float]:
        """Calculate MACD indicators."""
        try:
            if len(prices) < 26:
                return {}
            
            # Calculate EMAs
            ema_12 = DataProcessor._calculate_ema(prices, 12)
            ema_26 = DataProcessor._calculate_ema(prices, 26)
            
            # Calculate MACD line
            macd = ema_12 - ema_26
            
            # Calculate signal line (9-day EMA of MACD)
            # Simplified: use SMA instead of EMA for signal
            signal = macd  # Placeholder - would need MACD history for proper signal
            
            # Calculate histogram
            histogram = macd - signal
            
            return {
                'macd': round(macd, 4),
                'macd_signal': round(signal, 4),
                'macd_histogram': round(histogram, 4)
            }
            
        except Exception as e:
            logger.error(f"Error calculating MACD: {str(e)}")
            return {}
    
    @staticmethod
    def _calculate_ema(prices: List[float], period: int) -> float:
        """Calculate Exponential Moving Average."""
        try:
            if len(prices) < period:
                return statistics.mean(prices)
            
            # Start with SMA
            sma = statistics.mean(prices[:period])
            
            # Calculate EMA
            multiplier = 2 / (period + 1)
            ema = sma
            
            for price in prices[period:]:
                ema = (price * multiplier) + (ema * (1 - multiplier))
            
            return ema
            
        except Exception as e:
            logger.error(f"Error calculating EMA: {str(e)}")
            return statistics.mean(prices)
    
    @staticmethod
    def _calculate_bollinger_bands(prices: List[float], period: int = 20, std_dev: float = 2) -> Dict[str, float]:
        """Calculate Bollinger Bands."""
        try:
            if len(prices) < period:
                return {}
            
            # Calculate middle band (SMA)
            middle = statistics.mean(prices[-period:])
            
            # Calculate standard deviation
            variance = statistics.variance(prices[-period:])
            std = variance ** 0.5
            
            # Calculate upper and lower bands
            upper = middle + (std * std_dev)
            lower = middle - (std * std_dev)
            
            return {
                'bb_upper': round(upper, 2),
                'bb_middle': round(middle, 2),
                'bb_lower': round(lower, 2)
            }
            
        except Exception as e:
            logger.error(f"Error calculating Bollinger Bands: {str(e)}")
            return {}
    
    @staticmethod
    def _calculate_volatility(prices: List[float]) -> float:
        """Calculate price volatility."""
        try:
            if len(prices) < 2:
                return 0.0
            
            # Calculate daily returns
            returns = [(prices[i] - prices[i-1]) / prices[i-1] for i in range(1, len(prices))]
            
            # Calculate standard deviation of returns
            if len(returns) < 2:
                return 0.0
            
            volatility = statistics.stdev(returns)
            return round(volatility, 6)
            
        except Exception as e:
            logger.error(f"Error calculating volatility: {str(e)}")
            return 0.0
    
    @staticmethod
    def _calculate_support_resistance(closes: List[float], highs: List[float], lows: List[float]) -> Tuple[float, float]:
        """Calculate support and resistance levels."""
        try:
            if len(closes) < 20:
                return min(closes), max(closes)
            
            # Simple support/resistance calculation
            recent_closes = closes[-20:]
            recent_highs = highs[-20:] if len(highs) >= 20 else closes[-20:]
            recent_lows = lows[-20:] if len(lows) >= 20 else closes[-20:]
            
            # Support is the lowest low in recent period
            support = min(recent_lows)
            
            # Resistance is the highest high in recent period
            resistance = max(recent_highs)
            
            return round(support, 2), round(resistance, 2)
            
        except Exception as e:
            logger.error(f"Error calculating support/resistance: {str(e)}")
            return min(closes), max(closes)
    
    @staticmethod
    def calculate_correlation(prices1: List[float], prices2: List[float]) -> float:
        """Calculate correlation between two price series."""
        try:
            if len(prices1) != len(prices2) or len(prices1) < 2:
                return 0.0
            
            # Calculate returns
            returns1 = [(prices1[i] - prices1[i-1]) / prices1[i-1] for i in range(1, len(prices1))]
            returns2 = [(prices2[i] - prices2[i-1]) / prices2[i-1] for i in range(1, len(prices2))]
            
            # Calculate correlation coefficient
            if len(returns1) < 2:
                return 0.0
            
            correlation = statistics.correlation(returns1, returns2)
            return round(correlation, 3)
            
        except Exception as e:
            logger.error(f"Error calculating correlation: {str(e)}")
            return 0.0
    
    @staticmethod
    def calculate_drawdown(prices: List[float]) -> Dict[str, float]:
        """Calculate maximum drawdown."""
        try:
            if len(prices) < 2:
                return {'max_drawdown': 0.0, 'current_drawdown': 0.0}
            
            # Calculate running maximum
            running_max = []
            current_max = prices[0]
            
            for price in prices:
                if price > current_max:
                    current_max = price
                running_max.append(current_max)
            
            # Calculate drawdowns
            drawdowns = [(prices[i] - running_max[i]) / running_max[i] for i in range(len(prices))]
            
            max_drawdown = min(drawdowns)
            current_drawdown = drawdowns[-1]
            
            return {
                'max_drawdown': round(max_drawdown, 4),
                'current_drawdown': round(current_drawdown, 4)
            }
            
        except Exception as e:
            logger.error(f"Error calculating drawdown: {str(e)}")
            return {'max_drawdown': 0.0, 'current_drawdown': 0.0}
    
    @staticmethod
    def calculate_sharpe_ratio(returns: List[float], risk_free_rate: float = 0.02) -> float:
        """Calculate Sharpe ratio."""
        try:
            if len(returns) < 2:
                return 0.0
            
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            
            if std_return == 0:
                return 0.0
            
            # Annualized Sharpe ratio
            excess_return = mean_return - (risk_free_rate / 252)  # Daily risk-free rate
            sharpe_ratio = (excess_return / std_return) * (252 ** 0.5)
            
            return round(sharpe_ratio, 2)
            
        except Exception as e:
            logger.error(f"Error calculating Sharpe ratio: {str(e)}")
            return 0.0
    
    @staticmethod
    def detect_chart_patterns(prices: List[float]) -> List[str]:
        """Detect simple chart patterns."""
        try:
            if len(prices) < 10:
                return []
            
            patterns = []
            
            # Moving average crossovers
            if len(prices) >= 20:
                sma_short = statistics.mean(prices[-10:])
                sma_long = statistics.mean(prices[-20:])
                
                if sma_short > sma_long:
                    patterns.append("Golden Cross")
                elif sma_short < sma_long:
                    patterns.append("Death Cross")
            
            # Price momentum
            recent_prices = prices[-5:]
            if len(recent_prices) >= 5:
                if all(recent_prices[i] > recent_prices[i-1] for i in range(1, len(recent_prices))):
                    patterns.append("Uptrend")
                elif all(recent_prices[i] < recent_prices[i-1] for i in range(1, len(recent_prices))):
                    patterns.append("Downtrend")
            
            # Support/Resistance breakout
            if len(prices) >= 20:
                support, resistance = DataProcessor._calculate_support_resistance(prices, prices, prices)
                current_price = prices[-1]
                
                if current_price > resistance:
                    patterns.append("Resistance Breakout")
                elif current_price < support:
                    patterns.append("Support Breakdown")
            
            return patterns
            
        except Exception as e:
            logger.error(f"Error detecting chart patterns: {str(e)}")
            return []
    
    @staticmethod
    def analyze_volume_profile(volumes: List[float], prices: List[float]) -> Dict[str, Any]:
        """Analyze volume profile."""
        try:
            if len(volumes) != len(prices) or len(volumes) < 10:
                return {}
            
            # Calculate volume-weighted average price (VWAP)
            total_volume = sum(volumes)
            if total_volume == 0:
                return {}
            
            vwap = sum(prices[i] * volumes[i] for i in range(len(prices))) / total_volume
            
            # Calculate volume trend
            recent_volume = statistics.mean(volumes[-5:])
            historical_volume = statistics.mean(volumes[:-5]) if len(volumes) > 5 else recent_volume
            
            volume_trend = "increasing" if recent_volume > historical_volume else "decreasing"
            
            return {
                'vwap': round(vwap, 2),
                'avg_volume': round(statistics.mean(volumes), 0),
                'volume_trend': volume_trend,
                'volume_ratio': round(recent_volume / historical_volume, 2) if historical_volume > 0 else 1.0
            }
            
        except Exception as e:
            logger.error(f"Error analyzing volume profile: {str(e)}")
            return {}
    
    @staticmethod
    def calculate_portfolio_metrics(positions: List[Dict[str, Any]]) -> Dict[str, float]:
        """Calculate portfolio-level metrics."""
        try:
            if not positions:
                return {}
            
            # Extract values
            values = [pos.get('market_value', 0) for pos in positions]
            total_value = sum(values)
            
            if total_value == 0:
                return {}
            
            # Calculate weights
            weights = [value / total_value for value in values]
            
            # Calculate portfolio concentration
            herfindahl_index = sum(w**2 for w in weights)
            
            # Calculate effective number of holdings
            effective_holdings = 1 / herfindahl_index if herfindahl_index > 0 else 0
            
            # Calculate diversification metrics
            max_weight = max(weights)
            top_5_concentration = sum(sorted(weights, reverse=True)[:5])
            
            return {
                'total_value': total_value,
                'number_of_positions': len(positions),
                'herfindahl_index': round(herfindahl_index, 4),
                'effective_holdings': round(effective_holdings, 2),
                'max_position_weight': round(max_weight, 4),
                'top_5_concentration': round(top_5_concentration, 4)
            }
            
        except Exception as e:
            logger.error(f"Error calculating portfolio metrics: {str(e)}")
            return {}
    
    @staticmethod
    def normalize_price_data(price_data: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Normalize and clean price data."""
        try:
            if not price_data:
                return []
            
            cleaned_data = []
            
            for item in price_data:
                # Validate and clean each data point
                try:
                    cleaned_item = {
                        'date': item.get('date', ''),
                        'open': float(item.get('open', 0)),
                        'high': float(item.get('high', 0)),
                        'low': float(item.get('low', 0)),
                        'close': float(item.get('close', 0)),
                        'volume': float(item.get('volume', 0))
                    }
                    
                    # Basic validation
                    if (cleaned_item['close'] > 0 and 
                        cleaned_item['high'] >= cleaned_item['low'] and
                        cleaned_item['high'] >= cleaned_item['close'] and
                        cleaned_item['low'] <= cleaned_item['close']):
                        cleaned_data.append(cleaned_item)
                        
                except (ValueError, TypeError) as e:
                    logger.warning(f"Skipping invalid price data point: {str(e)}")
                    continue
            
            return cleaned_data
            
        except Exception as e:
            logger.error(f"Error normalizing price data: {str(e)}")
            return price_data
    
    @staticmethod
    def calculate_risk_metrics(returns: List[float]) -> Dict[str, float]:
        """Calculate comprehensive risk metrics."""
        try:
            if len(returns) < 2:
                return {}
            
            # Basic statistics
            mean_return = statistics.mean(returns)
            std_return = statistics.stdev(returns)
            
            # Downside deviation
            negative_returns = [r for r in returns if r < 0]
            downside_deviation = statistics.stdev(negative_returns) if len(negative_returns) > 1 else 0
            
            # Value at Risk (VaR) - 95% confidence
            sorted_returns = sorted(returns)
            var_95 = sorted_returns[int(0.05 * len(sorted_returns))] if len(sorted_returns) > 20 else min(returns)
            
            # Maximum consecutive losses
            max_consecutive_losses = 0
            current_consecutive = 0
            
            for ret in returns:
                if ret < 0:
                    current_consecutive += 1
                    max_consecutive_losses = max(max_consecutive_losses, current_consecutive)
                else:
                    current_consecutive = 0
            
            return {
                'mean_return': round(mean_return, 6),
                'volatility': round(std_return, 6),
                'downside_deviation': round(downside_deviation, 6),
                'var_95': round(var_95, 6),
                'max_consecutive_losses': max_consecutive_losses
            }
            
        except Exception as e:
            logger.error(f"Error calculating risk metrics: {str(e)}")
            return {}
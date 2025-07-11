"""Email service for generating and sending portfolio reports."""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
import boto3
from botocore.exceptions import ClientError, NoCredentialsError
import jinja2
import os

from ..config.settings import Settings
from ..models.portfolio import Portfolio
from ..models.analysis import AssetAnalysis, Recommendation
from ..models.report import Report

logger = logging.getLogger(__name__)


class EmailService:
    """Email service for generating and sending HTML reports."""
    
    def __init__(self, settings: Settings):
        """Initialize email service."""
        self.settings = settings
        
        # Initialize SES client
        try:
            self.ses_client = boto3.client(
                'ses',
                region_name=settings.aws_region
            )
        except NoCredentialsError:
            logger.warning("AWS credentials not found. Email service will be limited.")
            self.ses_client = None
        
        # Initialize Jinja2 environment
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(searchpath=["assets/email_templates", "."]),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
        
        # Register custom filters
        self.jinja_env.filters['currency'] = self._format_currency
        self.jinja_env.filters['percentage'] = self._format_percentage
        self.jinja_env.filters['datetime'] = self._format_datetime
    
    def generate_html_report(self, portfolio: Portfolio, analyses: List[AssetAnalysis]) -> str:
        """Generate clean, minimal HTML email report."""
        try:
            logger.info("Generating HTML email report...")
            
            # Create report context
            context = self._create_report_context(portfolio, analyses)
            
            # Try to load custom template, fall back to default
            template_name = "report.html"
            
            try:
                template = self.jinja_env.get_template(template_name)
            except jinja2.TemplateNotFound:
                logger.warning(f"Template {template_name} not found, using default template")
                template = self._create_default_template()
            
            # Render template
            html_content = template.render(**context)
            
            logger.info("Successfully generated HTML report")
            return html_content
            
        except Exception as e:
            logger.error(f"Error generating HTML report: {str(e)}")
            return self._create_fallback_html(portfolio, analyses)
    
    def _create_report_context(self, portfolio: Portfolio, analyses: List[AssetAnalysis]) -> Dict[str, Any]:
        """Create context for report template."""
        try:
            # Calculate summary statistics
            total_value = portfolio.total_value
            total_positions = len(analyses)
            
            # Recommendation counts
            buy_count = sum(1 for a in analyses if a.recommendation == Recommendation.BUY)
            sell_count = sum(1 for a in analyses if a.recommendation == Recommendation.SELL)
            hold_count = sum(1 for a in analyses if a.recommendation == Recommendation.HOLD)
            
            # Performance metrics
            total_gain_loss = portfolio.total_gain_loss or 0
            total_gain_loss_percent = portfolio.total_gain_loss_percent or 0
            
            # Risk metrics
            high_risk_count = sum(1 for a in analyses if a.risk_assessment.risk_level in ['high', 'very_high'])
            avg_confidence = sum(a.confidence for a in analyses) / len(analyses) if analyses else 0
            
            # Sort analyses by market value
            sorted_analyses = sorted(analyses, key=lambda a: a.market_value, reverse=True)
            
            # Top positions
            top_positions = []
            for analysis in sorted_analyses[:5]:  # Top 5 positions
                position = portfolio.get_position_by_symbol(analysis.symbol)
                if position:
                    top_positions.append({
                        'symbol': analysis.symbol,
                        'company_name': getattr(position, 'company_name', '') or getattr(position, 'full_name', ''),
                        'market_value': position.market_value,
                        'percentage': (position.market_value / total_value) * 100,
                        'recommendation': analysis.recommendation.value,
                        'confidence': analysis.confidence,
                        'reasoning': analysis.reasoning
                    })
            
            # Key recommendations
            key_recommendations = []
            high_confidence_analyses = [a for a in analyses if a.confidence > 0.7]
            high_confidence_analyses.sort(key=lambda a: a.confidence, reverse=True)
            
            for analysis in high_confidence_analyses[:3]:  # Top 3 high-confidence recommendations
                key_recommendations.append({
                    'symbol': analysis.symbol,
                    'recommendation': analysis.recommendation.value,
                    'confidence': analysis.confidence,
                    'reasoning': analysis.reasoning
                })
            
            # Market highlights
            market_highlights = []
            for analysis in analyses:
                if analysis.sentiment_analysis.recent_news:
                    for news in analysis.sentiment_analysis.recent_news[:2]:  # Top 2 news per asset
                        market_highlights.append({
                            'symbol': analysis.symbol,
                            'title': news.title,
                            'source': news.source,
                            'sentiment': analysis.sentiment_analysis.sentiment_level.value,
                            'url': news.url
                        })
            
            # Sort market highlights by date
            market_highlights.sort(key=lambda x: x.get('date', ''), reverse=True)
            market_highlights = market_highlights[:10]  # Top 10 highlights
            
            # Create context
            context = {
                'report_date': datetime.now(),
                'portfolio': {
                    'total_value': total_value,
                    'total_positions': total_positions,
                    'stocks_count': len(portfolio.stocks),
                    'crypto_count': len(portfolio.crypto),
                    'stocks_percentage': portfolio.stocks_percentage,
                    'crypto_percentage': portfolio.crypto_percentage,
                    'total_gain_loss': total_gain_loss,
                    'total_gain_loss_percent': total_gain_loss_percent
                },
                'recommendations': {
                    'buy_count': buy_count,
                    'sell_count': sell_count,
                    'hold_count': hold_count,
                    'total_count': total_positions
                },
                'risk_metrics': {
                    'high_risk_count': high_risk_count,
                    'avg_confidence': avg_confidence,
                    'portfolio_risk': 'Medium'  # Simplified
                },
                'top_positions': top_positions,
                'key_recommendations': key_recommendations,
                'market_highlights': market_highlights,
                'analyses': sorted_analyses,
                'settings': self.settings
            }
            
            return context
            
        except Exception as e:
            logger.error(f"Error creating report context: {str(e)}")
            return {
                'report_date': datetime.now(),
                'portfolio': {'total_value': 0, 'total_positions': 0},
                'recommendations': {'buy_count': 0, 'sell_count': 0, 'hold_count': 0},
                'risk_metrics': {'high_risk_count': 0, 'avg_confidence': 0},
                'top_positions': [],
                'key_recommendations': [],
                'market_highlights': [],
                'analyses': [],
                'settings': self.settings
            }
    
    def _create_default_template(self) -> jinja2.Template:
        """Create default HTML template."""
        template_content = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Quantasaurus Rex - Portfolio Report</title>
    <style>
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            line-height: 1.6;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }
        .container {
            max-width: 800px;
            margin: 0 auto;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
            overflow: hidden;
        }
        .header {
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            padding: 30px;
            text-align: center;
        }
        .header h1 {
            margin: 0;
            font-size: 2.5em;
            font-weight: 300;
        }
        .header p {
            margin: 10px 0 0 0;
            font-size: 1.2em;
            opacity: 0.9;
        }
        .summary {
            background: #f8f9fa;
            padding: 30px;
            border-bottom: 1px solid #e9ecef;
        }
        .summary h2 {
            margin-top: 0;
            color: #495057;
        }
        .metrics {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 20px;
            margin: 20px 0;
        }
        .metric {
            background: white;
            padding: 20px;
            border-radius: 8px;
            text-align: center;
            box-shadow: 0 2px 4px rgba(0, 0, 0, 0.1);
        }
        .metric-value {
            font-size: 2em;
            font-weight: bold;
            color: #667eea;
        }
        .metric-label {
            color: #6c757d;
            font-size: 0.9em;
            margin-top: 5px;
        }
        .section {
            padding: 30px;
            border-bottom: 1px solid #e9ecef;
        }
        .section h2 {
            color: #495057;
            margin-top: 0;
            margin-bottom: 20px;
        }
        .position-card {
            background: white;
            border: 1px solid #e9ecef;
            border-radius: 8px;
            padding: 20px;
            margin-bottom: 20px;
            transition: box-shadow 0.2s;
        }
        .position-card:hover {
            box-shadow: 0 4px 8px rgba(0, 0, 0, 0.15);
        }
        .position-header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 15px;
        }
        .position-symbol {
            font-size: 1.5em;
            font-weight: bold;
            color: #495057;
        }
        .position-company {
            color: #6c757d;
            font-size: 0.9em;
        }
        .recommendation {
            padding: 5px 15px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 0.9em;
            text-transform: uppercase;
        }
        .recommendation.buy {
            background: #d4edda;
            color: #155724;
        }
        .recommendation.sell {
            background: #f8d7da;
            color: #721c24;
        }
        .recommendation.hold {
            background: #fff3cd;
            color: #856404;
        }
        .position-details {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
            gap: 15px;
            margin-bottom: 15px;
        }
        .detail-item {
            text-align: center;
        }
        .detail-value {
            font-size: 1.2em;
            font-weight: bold;
            color: #495057;
        }
        .detail-label {
            color: #6c757d;
            font-size: 0.8em;
        }
        .reasoning {
            background: #f8f9fa;
            padding: 15px;
            border-radius: 6px;
            font-size: 0.9em;
            color: #495057;
            margin-top: 15px;
        }
        .confidence-bar {
            width: 100%;
            height: 8px;
            background: #e9ecef;
            border-radius: 4px;
            overflow: hidden;
            margin-top: 10px;
        }
        .confidence-fill {
            height: 100%;
            background: linear-gradient(90deg, #dc3545 0%, #ffc107 50%, #28a745 100%);
            transition: width 0.3s ease;
        }
        .footer {
            background: #495057;
            color: white;
            padding: 20px;
            text-align: center;
            font-size: 0.9em;
        }
        .footer a {
            color: #adb5bd;
            text-decoration: none;
        }
        .disclaimer {
            background: #fff3cd;
            border: 1px solid #ffeaa7;
            padding: 15px;
            margin: 20px 0;
            border-radius: 6px;
            font-size: 0.9em;
            color: #856404;
        }
        @media (max-width: 600px) {
            .metrics {
                grid-template-columns: 1fr;
            }
            .position-header {
                flex-direction: column;
                align-items: flex-start;
            }
            .position-details {
                grid-template-columns: 1fr 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>🦕 Quantasaurus Rex</h1>
            <p>AI-Powered Portfolio Analysis</p>
            <p>{{ report_date | datetime }}</p>
        </div>
        
        <div class="summary">
            <h2>Portfolio Summary</h2>
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value">{{ portfolio.total_value | currency }}</div>
                    <div class="metric-label">Total Value</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ portfolio.total_positions }}</div>
                    <div class="metric-label">Total Positions</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ portfolio.total_gain_loss_percent | percentage }}</div>
                    <div class="metric-label">Daily P&L</div>
                </div>
                <div class="metric">
                    <div class="metric-value">{{ risk_metrics.avg_confidence | percentage }}</div>
                    <div class="metric-label">Avg Confidence</div>
                </div>
            </div>
            
            <div class="metrics">
                <div class="metric">
                    <div class="metric-value" style="color: #28a745;">{{ recommendations.buy_count }}</div>
                    <div class="metric-label">BUY</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #ffc107;">{{ recommendations.hold_count }}</div>
                    <div class="metric-label">HOLD</div>
                </div>
                <div class="metric">
                    <div class="metric-value" style="color: #dc3545;">{{ recommendations.sell_count }}</div>
                    <div class="metric-label">SELL</div>
                </div>
            </div>
        </div>
        
        {% if key_recommendations %}
        <div class="section">
            <h2>Key Recommendations</h2>
            {% for rec in key_recommendations %}
            <div class="position-card">
                <div class="position-header">
                    <div>
                        <div class="position-symbol">{{ rec.symbol }}</div>
                    </div>
                    <div class="recommendation {{ rec.recommendation.lower() }}">{{ rec.recommendation }}</div>
                </div>
                <div class="reasoning">{{ rec.reasoning }}</div>
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: {{ rec.confidence | percentage }}"></div>
                </div>
            </div>
            {% endfor %}
        </div>
        {% endif %}
        
        <div class="section">
            <h2>Portfolio Positions</h2>
            {% for analysis in analyses %}
            <div class="position-card">
                <div class="position-header">
                    <div>
                        <div class="position-symbol">{{ analysis.symbol }}</div>
                        <div class="position-company">{{ analysis.asset_type | title }}</div>
                    </div>
                    <div class="recommendation {{ analysis.recommendation.value.lower() }}">{{ analysis.recommendation.value }}</div>
                </div>
                
                <div class="position-details">
                    <div class="detail-item">
                        <div class="detail-value">{{ analysis.market_value | currency }}</div>
                        <div class="detail-label">Market Value</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value">{{ analysis.current_price | currency }}</div>
                        <div class="detail-label">Current Price</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value">{{ analysis.confidence | percentage }}</div>
                        <div class="detail-label">Confidence</div>
                    </div>
                    <div class="detail-item">
                        <div class="detail-value">{{ analysis.risk_assessment.risk_level | title }}</div>
                        <div class="detail-label">Risk Level</div>
                    </div>
                </div>
                
                <div class="reasoning">
                    <strong>Analysis:</strong> {{ analysis.reasoning }}
                </div>
                
                <div class="confidence-bar">
                    <div class="confidence-fill" style="width: {{ analysis.confidence | percentage }}"></div>
                </div>
            </div>
            {% endfor %}
        </div>
        
        <div class="disclaimer">
            <strong>Disclaimer:</strong> This report is generated by AI and is for informational purposes only. 
            It should not be considered as financial advice. Always consult with a qualified financial advisor 
            before making investment decisions.
        </div>
        
        <div class="footer">
            <p>🤖 Generated with AI by Quantasaurus Rex</p>
            <p>Report generated at {{ report_date | datetime }}</p>
        </div>
    </div>
</body>
</html>
        """
        
        return jinja2.Template(template_content)
    
    def _create_fallback_html(self, portfolio: Portfolio, analyses: List[AssetAnalysis]) -> str:
        """Create fallback HTML if template fails."""
        try:
            html = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <title>Quantasaurus Rex - Portfolio Report</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 40px; }}
                    .header {{ background: #2c3e50; color: white; padding: 20px; text-align: center; }}
                    .summary {{ background: #ecf0f1; padding: 15px; margin: 20px 0; }}
                    .asset {{ border: 1px solid #bdc3c7; margin: 10px 0; padding: 15px; }}
                    .buy {{ color: #27ae60; }}
                    .sell {{ color: #e74c3c; }}
                    .hold {{ color: #f39c12; }}
                </style>
            </head>
            <body>
                <div class="header">
                    <h1>🦕 Quantasaurus Rex</h1>
                    <p>Daily Portfolio Analysis</p>
                    <p>{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                </div>
                
                <div class="summary">
                    <h2>Portfolio Summary</h2>
                    <p>Total Value: ${portfolio.total_value:,.2f}</p>
                    <p>Total Positions: {len(analyses)}</p>
                    <p>Stocks: {len(portfolio.stocks)} | Crypto: {len(portfolio.crypto)}</p>
                </div>
                
                <h2>Analysis Results</h2>
            """
            
            for analysis in analyses:
                html += f"""
                <div class="asset">
                    <h3>{analysis.symbol}</h3>
                    <p class="{analysis.recommendation.value.lower()}">
                        <strong>{analysis.recommendation.value}</strong>
                    </p>
                    <p>Market Value: ${analysis.market_value:,.2f}</p>
                    <p>Confidence: {analysis.confidence:.1%}</p>
                    <p>Reasoning: {analysis.reasoning}</p>
                </div>
                """
            
            html += """
                <div class="footer">
                    <p>Generated by Quantasaurus Rex AI Agent</p>
                </div>
            </body>
            </html>
            """
            
            return html
            
        except Exception as e:
            logger.error(f"Error creating fallback HTML: {str(e)}")
            return f"<html><body><h1>Error generating report</h1><p>{str(e)}</p></body></html>"
    
    async def send_report(self, html_content: str, subject: Optional[str] = None) -> bool:
        """Send email report via SES."""
        try:
            if not self.ses_client:
                logger.error("SES client not available")
                return False
            
            logger.info(f"Sending email report to {self.settings.email_recipient}")
            
            # Default subject
            if not subject:
                subject = f"🦕 Quantasaurus Rex Daily Portfolio Report - {datetime.now().strftime('%Y-%m-%d')}"
            
            # Send email
            response = self.ses_client.send_email(
                Source=self.settings.email_sender,
                Destination={'ToAddresses': [self.settings.email_recipient]},
                Message={
                    'Subject': {'Data': subject, 'Charset': 'UTF-8'},
                    'Body': {
                        'Html': {'Data': html_content, 'Charset': 'UTF-8'},
                        'Text': {'Data': self._html_to_text(html_content), 'Charset': 'UTF-8'}
                    }
                }
            )
            
            message_id = response['MessageId']
            logger.info(f"Email sent successfully. Message ID: {message_id}")
            return True
            
        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']
            logger.error(f"SES error ({error_code}): {error_message}")
            return False
        except Exception as e:
            logger.error(f"Error sending email: {str(e)}")
            return False
    
    def _html_to_text(self, html_content: str) -> str:
        """Convert HTML to plain text for email."""
        try:
            # Simple HTML to text conversion
            import re
            
            # Remove HTML tags
            text = re.sub(r'<[^>]+>', ' ', html_content)
            
            # Clean up whitespace
            text = re.sub(r'\s+', ' ', text)
            text = text.strip()
            
            return text
            
        except Exception as e:
            logger.error(f"Error converting HTML to text: {str(e)}")
            return "Portfolio report (HTML version available)"
    
    def _format_currency(self, value: float) -> str:
        """Format currency values."""
        try:
            return f"${value:,.2f}"
        except:
            return f"${value}"
    
    def _format_percentage(self, value: float) -> str:
        """Format percentage values."""
        try:
            return f"{value:.1%}"
        except:
            return f"{value * 100:.1f}%"
    
    def _format_datetime(self, value: datetime) -> str:
        """Format datetime values."""
        try:
            return value.strftime('%Y-%m-%d %H:%M:%S UTC')
        except:
            return str(value)
    
    async def verify_email_address(self, email: str) -> bool:
        """Verify email address with SES."""
        try:
            if not self.ses_client:
                logger.error("SES client not available")
                return False
            
            response = self.ses_client.verify_email_identity(EmailAddress=email)
            logger.info(f"Email verification sent to {email}")
            return True
            
        except ClientError as e:
            logger.error(f"Error verifying email {email}: {str(e)}")
            return False
    
    async def get_send_quota(self) -> Dict[str, float]:
        """Get SES send quota."""
        try:
            if not self.ses_client:
                return {}
            
            response = self.ses_client.get_send_quota()
            return {
                'max_24_hour': response['Max24HourSend'],
                'max_send_rate': response['MaxSendRate'],
                'sent_last_24_hours': response['SentLast24Hours']
            }
            
        except ClientError as e:
            logger.error(f"Error getting send quota: {str(e)}")
            return {}
    
    async def close(self):
        """Close the email service."""
        # SES client doesn't need explicit closing
        pass
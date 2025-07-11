"""
Email Generation and Delivery

Handles email generation and delivery including:
- HTML email templates with responsive design
- Portfolio analysis summaries
- Individual asset recommendations
- AWS SES integration for delivery
"""

from typing import Dict, Any, List
import boto3
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from jinja2 import Environment, FileSystemLoader
import structlog
from datetime import datetime

from quantasaurus.utils.config import Config
from quantasaurus.utils.exceptions import EmailGenerationError

logger = structlog.get_logger()


class EmailGenerator:
    """Handles email generation and delivery."""
    
    def __init__(self, config: Config):
        self.config = config
        self.ses_client = boto3.client('ses', region_name=config.ses_region)
        
        # Set up Jinja2 template environment
        self.template_env = Environment(
            loader=FileSystemLoader('quantasaurus/templates')
        )
    
    def generate_and_send_email(self, portfolio_data: Dict[str, Any], 
                               recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Generate and send email with portfolio analysis.
        
        Args:
            portfolio_data: Portfolio and market data
            recommendations: AI-generated recommendations
            
        Returns:
            Email delivery result
        """
        try:
            logger.info("Generating and sending portfolio analysis email")
            
            # Generate email content
            email_content = self.generate_email_content(portfolio_data, recommendations)
            
            # Send email
            result = self._send_email(email_content)
            
            logger.info("Email sent successfully", message_id=result.get("message_id"))
            return result
            
        except Exception as e:
            logger.error("Failed to generate and send email", error=str(e))
            raise EmailGenerationError(f"Failed to send email: {str(e)}", "EMAIL_SEND_FAILED")
    
    def generate_email_content(self, portfolio_data: Dict[str, Any], 
                              recommendations: List[Dict[str, Any]]) -> Dict[str, str]:
        """
        Generate email content from portfolio data and recommendations.
        
        Args:
            portfolio_data: Portfolio and market data
            recommendations: AI-generated recommendations
            
        Returns:
            Email content dictionary with HTML and text versions
        """
        try:
            logger.info("Generating email content")
            
            # Prepare template context
            context = {
                "date": datetime.now().strftime("%B %d, %Y"),
                "portfolio": portfolio_data["portfolio"],
                "recommendations": recommendations,
                "summary": self._generate_summary(portfolio_data, recommendations),
                "market_news": portfolio_data.get("news", {}).get("market_news", [])[:5]
            }
            
            # Load and render HTML template
            html_template = self.template_env.get_template('portfolio_analysis.html')
            html_content = html_template.render(**context)
            
            # Generate plain text version
            text_content = self._generate_text_content(context)
            
            return {
                "html": html_content,
                "text": text_content,
                "subject": f"{self.config.email_subject_prefix} Daily Portfolio Analysis - {context['date']}"
            }
            
        except Exception as e:
            logger.error("Failed to generate email content", error=str(e))
            raise EmailGenerationError(f"Failed to generate email: {str(e)}", "EMAIL_GENERATION_FAILED")
    
    def _generate_summary(self, portfolio_data: Dict[str, Any], 
                         recommendations: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate portfolio summary statistics."""
        total_value = portfolio_data["portfolio"]["total_value"]
        day_change = portfolio_data["portfolio"]["day_change"]
        
        # Count recommendations by type
        buy_count = len([r for r in recommendations if r["recommendation"] == "BUY"])
        hold_count = len([r for r in recommendations if r["recommendation"] == "HOLD"])
        sell_count = len([r for r in recommendations if r["recommendation"] == "SELL"])
        
        # Calculate average confidence
        avg_confidence = sum(r["confidence"] for r in recommendations) / len(recommendations) if recommendations else 0
        
        return {
            "total_value": total_value,
            "day_change": day_change,
            "day_change_percent": (day_change / total_value) * 100 if total_value > 0 else 0,
            "total_positions": len(portfolio_data["positions"]),
            "recommendations_count": len(recommendations),
            "buy_count": buy_count,
            "hold_count": hold_count,
            "sell_count": sell_count,
            "avg_confidence": avg_confidence
        }
    
    def _generate_text_content(self, context: Dict[str, Any]) -> str:
        """Generate plain text version of email."""
        lines = []
        lines.append(f"QUANTASAURUS-REX DAILY PORTFOLIO ANALYSIS")
        lines.append(f"Date: {context['date']}")
        lines.append("")
        
        summary = context["summary"]
        lines.append("PORTFOLIO SUMMARY")
        lines.append(f"Total Value: ${summary['total_value']:,.2f}")
        lines.append(f"Day Change: ${summary['day_change']:,.2f} ({summary['day_change_percent']:+.2f}%)")
        lines.append(f"Total Positions: {summary['total_positions']}")
        lines.append("")
        
        lines.append("RECOMMENDATIONS")
        lines.append(f"Total Recommendations: {summary['recommendations_count']}")
        lines.append(f"Buy: {summary['buy_count']}, Hold: {summary['hold_count']}, Sell: {summary['sell_count']}")
        lines.append(f"Average Confidence: {summary['avg_confidence']:.1f}%")
        lines.append("")
        
        for rec in context["recommendations"]:
            lines.append(f"{rec['symbol']} - {rec['recommendation']} ({rec['confidence']}% confidence)")
            lines.append(f"  Current Value: ${rec['current_value']:,.2f}")
            lines.append(f"  Reasoning: {', '.join(rec['reasoning'][:2])}")
            lines.append("")
        
        lines.append("DISCLAIMER")
        lines.append("This analysis is for informational purposes only and should not be considered")
        lines.append("as financial advice. Always consult with a qualified financial advisor.")
        
        return "\n".join(lines)
    
    def _send_email(self, email_content: Dict[str, str]) -> Dict[str, Any]:
        """Send email using AWS SES."""
        try:
            response = self.ses_client.send_email(
                Source=self.config.from_email,
                Destination={'ToAddresses': [self.config.to_email]},
                Message={
                    'Subject': {'Data': email_content["subject"]},
                    'Body': {
                        'Text': {'Data': email_content["text"]},
                        'Html': {'Data': email_content["html"]}
                    }
                }
            )
            
            return {
                "status": "success",
                "message_id": response["MessageId"],
                "subject": email_content["subject"]
            }
            
        except Exception as e:
            logger.error("Failed to send email via SES", error=str(e))
            raise EmailGenerationError(f"Failed to send email via SES: {str(e)}", "SES_SEND_FAILED")
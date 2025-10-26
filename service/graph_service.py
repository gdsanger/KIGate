"""
Microsoft Graph API service for sending emails
"""
import logging
from typing import Optional
import httpx
from msal import ConfidentialClientApplication
from jinja2 import Environment, FileSystemLoader
import config

logger = logging.getLogger(__name__)


class GraphService:
    """Service for Microsoft Graph API operations"""
    
    def __init__(self):
        self.client_id = config.ClientID
        self.tenant_id = config.TenantID
        self.client_secret = config.ClientSecret
        # Normalize base URL to avoid duplicate /v1.0 segments
        raw_base_url = config.BaseUrl or "https://graph.microsoft.com"
        self.base_url = self._normalize_base_url(raw_base_url)
        self.sender = config.Sender
        
        # Initialize MSAL app only if all required config is available
        self.app = None
        if self.client_id and self.tenant_id and self.client_secret:
            try:
                self.app = ConfidentialClientApplication(
                    client_id=self.client_id,
                    client_credential=self.client_secret,
                    authority=f"https://login.microsoftonline.com/{self.tenant_id}"
                )
            except Exception as e:
                logger.error(f"Failed to initialize MSAL app: {e}")
                self.app = None
        
        # Jinja2 environment for templates
        self.jinja_env = Environment(
            loader=FileSystemLoader("templates/mail"),
            autoescape=True
        )
    
    def _normalize_base_url(self, base_url: str) -> str:
        """Normalize base URL to ensure consistent Graph API endpoint construction"""
        # Remove trailing slashes
        normalized = base_url.rstrip('/')
        
        # Remove /v1.0 suffix if present to avoid duplication
        if normalized.endswith('/v1.0'):
            normalized = normalized[:-5]
        
        return normalized
    
    async def _get_access_token(self) -> Optional[str]:
        """Get access token for Graph API"""
        if not self.app:
            logger.error("MSAL app not initialized. Check your Graph API configuration.")
            return None
            
        try:
            # Get token for Graph API scope
            result = self.app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" in result:
                return result["access_token"]
            else:
                logger.error(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
                return None
                
        except Exception as e:
            logger.error(f"Error acquiring access token: {e}")
            return None
    
    async def send_email(
        self, 
        to_email: str, 
        subject: str, 
        html_content: str,
        text_content: Optional[str] = None
    ) -> bool:
        """Send email via Microsoft Graph API"""
        # Check if service is properly configured
        if not self.app:
            logger.error("Graph API not configured. Missing ClientID, TenantID or ClientSecret.")
            return False
            
        try:
            # Get access token
            token = await self._get_access_token()
            if not token:
                logger.error("Could not acquire access token")
                return False
            
            # Prepare email data
            email_data = {
                "message": {
                    "subject": subject,
                    "body": {
                        "contentType": "HTML",
                        "content": html_content
                    },
                    "toRecipients": [
                        {
                            "emailAddress": {
                                "address": to_email
                            }
                        }
                    ],
                    "from": {
                        "emailAddress": {
                            "address": self.sender
                        }
                    }
                },
                "saveToSentItems": "true"
            }
            
            # Add text content if provided
            if text_content:
                email_data["message"]["body"]["content"] = f"{html_content}\n\n{text_content}"
            
            # Send email
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json"
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{self.base_url}/v1.0/users/{self.sender}/sendMail",
                    json=email_data,
                    headers=headers
                )
                
                if response.status_code == 202:
                    logger.info(f"Email successfully sent to {to_email}")
                    return True
                else:
                    logger.error(f"Failed to send email. Status: {response.status_code}, Response: {response.text}")
                    return False
                    
        except Exception as e:
            logger.error(f"Error sending email: {e}")
            return False
    
    async def send_new_user_credentials_email(
        self, 
        user_name: str, 
        user_email: str, 
        client_id: str, 
        client_secret: str
    ) -> bool:
        """Send email with new user credentials"""
        try:
            # Render HTML template
            template = self.jinja_env.get_template("new_user_credentials.html")
            html_content = template.render(
                user_name=user_name,
                client_id=client_id,
                client_secret=client_secret,
                sender_email=self.sender
            )
            
            subject = f"KIGate API - Ihre neuen Zugangsdaten"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending new user credentials email: {e}")
            return False
    
    async def send_secret_regenerated_email(
        self, 
        user_name: str, 
        user_email: str, 
        client_id: str, 
        new_client_secret: str
    ) -> bool:
        """Send email when client secret is regenerated"""
        try:
            # Render HTML template (reuse the same template)
            template = self.jinja_env.get_template("new_user_credentials.html")
            html_content = template.render(
                user_name=user_name,
                client_id=client_id,
                client_secret=new_client_secret,
                sender_email=self.sender
            )
            
            subject = f"KIGate API - Ihr Client Secret wurde erneuert"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending secret regenerated email: {e}")
            return False
    
    async def send_admin_user_credentials_email(
        self, 
        user_name: str, 
        user_email: str, 
        username: str, 
        password: str
    ) -> bool:
        """Send email with new admin user credentials"""
        try:
            # Render HTML template
            template = self.jinja_env.get_template("admin_user_credentials.html")
            html_content = template.render(
                user_name=user_name,
                username=username,
                password=password,
                sender_email=self.sender
            )
            
            subject = f"KIGate Admin-Panel - Ihre neuen Zugangsdaten"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending admin user credentials email: {e}")
            return False
    
    async def send_admin_password_reset_email(
        self, 
        user_name: str, 
        user_email: str, 
        username: str, 
        new_password: str
    ) -> bool:
        """Send email when admin user password is reset"""
        try:
            # Render HTML template
            template = self.jinja_env.get_template("admin_password_reset.html")
            html_content = template.render(
                user_name=user_name,
                username=username,
                new_password=new_password,
                sender_email=self.sender
            )
            
            subject = f"KIGate Admin-Panel - Ihr Passwort wurde zurückgesetzt"
            
            return await self.send_email(
                to_email=user_email,
                subject=subject,
                html_content=html_content
            )
            
        except Exception as e:
            logger.error(f"Error sending admin password reset email: {e}")
            return False


# Global instance
_graph_service = None


def get_graph_service() -> GraphService:
    """Get singleton instance of GraphService"""
    global _graph_service
    if _graph_service is None:
        _graph_service = GraphService()
    return _graph_service

import smtplib
import configparser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from typing import List, Optional
from pathlib import Path

class EmailSender:
    def __init__(self, config_path: str = "mail_credential.ini"):
        """
        Initialize EmailSender with credentials from config file
        
        Args:
            config_path: Path to credential config file (default: mail_credential.ini)
        """
        self.config = configparser.ConfigParser()
        config_file = Path(__file__).parent / config_path
        
        if not config_file.exists():
            raise FileNotFoundError(f"Config file not found: {config_file}")
            
        self.config.read(config_file)
        
        try:
            self.smtp_server = self.config['SMTP']['server']
            self.smtp_port = self.config['SMTP'].getint('port')
            self.username = self.config['Credentials']['username']
            self.password = self.config['Credentials']['password']
        except KeyError as e:
            raise KeyError(f"Missing required configuration: {str(e)}")

    def send_html_email(
        self,
        to_emails: List[str],
        subject: str,
        html_content: str,
        from_email: Optional[str] = None
    ) -> bool:
        """
        Send HTML email to specified recipients
        
        Args:
            to_emails: List of recipient email addresses
            subject: Email subject line
            html_content: HTML content for email body
            from_email: Sender email address (optional, defaults to username)
            
        Returns:
            bool: True if email sent successfully, False otherwise
        """
        try:
            # Create message container
            msg = MIMEMultipart('alternative')
            msg['Subject'] = subject
            msg['From'] = from_email or self.username
            msg['To'] = ", ".join(to_emails)

            # Create HTML part
            html_part = MIMEText(html_content, 'html')
            msg.attach(html_part)

            # Create SMTP connection
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.username, self.password)
                server.send_message(msg)
                
            return True

        except Exception as e:
            print(f"Failed to send email: {str(e)}")
            return False

# Example usage:
"""
# Example mail_credential.ini format:
[SMTP]
server = smtp.gmail.com
port = 587

[Credentials]
username = your-email@gmail.com
password = your-app-password

# Usage
sender = EmailSender()
html_content = '''
<html>
    <body>
        <h1>Hello</h1>
        <p>This is a test email with <b>HTML</b> content.</p>
    </body>
</html>
'''

success = sender.send_html_email(
    to_emails=["recipient@example.com"],
    subject="Test HTML Email",
    html_content=html_content
)
"""


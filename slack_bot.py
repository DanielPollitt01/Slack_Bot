# README
# ======
# Simple Slack Messaging
# 
# This is a simple Slack messaging utility that allows you to send messages to Slack users.
# I found myself needing to rewrite this over and over so created this as a generic class to call in my projects.
#
# Setup:
# 1. Install dependencies:
#    pip install slack-sdk python-dotenv
#
# 2. Create .env or add this to your existing file with:
#    SLACK_BOT_TOKEN=xoxb-your-token
#    SLACK_LOG_PATH=logs (optional)
#    SLACK_LOG_LEVEL=INFO (optional)
#
# Usage:
#    from slack_bot import SlackMessenger
#    
#    # Initialize
#    slack = SlackMessenger()
#    
#    # Send simple message
#    slack.send_dm("U1234567", "Hello!")
#    
#    # Send formatted message
#    slack.send_dm("U1234567", "*Bold* message", formatting=True)
#    
#    # Send with file
#    slack.send_dm("U1234567", "See attachment", file_path="file.pdf")
#
# Notes:
# - Requires Slack bot token with chat:write, files:write, im:write scopes
# - Logs are stored in ./logs by default
# - Supports files up to 10MB (.pdf, .doc, .docx, .xls, .xlsx, .jpg, .png, .gif)

"""
Slack Messaging Utility
A reusable interface for sending Slack messages with support for formatting and file attachments.
"""

import os
import logging
from pathlib import Path
from typing import Optional, Union
from datetime import datetime
from logging.handlers import RotatingFileHandler

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class SlackMessenger:
    """A utility class for sending Slack direct messages with support for formatting and attachments."""
    
    def __init__(self, token: Optional[str] = None):
        """
        Initialize the SlackMessenger with a bot token.
        
        Args:
            token (Optional[str]): Slack bot token. If not provided, will look for SLACK_BOT_TOKEN in environment.
        """
        self.token = token or os.getenv('SLACK_BOT_TOKEN')
        if not self.token:
            raise ValueError("Slack bot token not provided and SLACK_BOT_TOKEN not found in environment")
        
        # Start Slack client
        self.client = WebClient(token=self.token)
        
        # Set up configuration
        self.config = {
            'max_retries': 3,
            'timeout': 30,
            'max_file_size': 10 * 1024 * 1024,  # 10MB
            'allowed_file_types': ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.jpg', '.png', '.gif', '.txt']
        }
        
        # Set up logging
        self._setup_logging()
    
    def _setup_logging(self) -> None:
        """Configure the logging system with rotation and formatting."""
        log_path = os.getenv('SLACK_LOG_PATH', 'logs')
        log_level = os.getenv('SLACK_LOG_LEVEL', 'INFO')
        
        # Create logs directory if it doesn't exist
        Path(log_path).mkdir(parents=True, exist_ok=True)
        
        # Configure logging
        log_file = Path(log_path) / 'slack_messenger.log'
        formatter = logging.Formatter('[%(asctime)s] [%(levelname)s] %(message)s')
        
        # Set up rotating file handler
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=1024 * 1024,  # 1MB
            backupCount=7  # Keep 7 days of logs
        )
        file_handler.setFormatter(formatter)
        
        # Configure logger
        self.logger = logging.getLogger('slack_messenger')
        self.logger.setLevel(getattr(logging, log_level.upper()))
        self.logger.addHandler(file_handler)
    
    def _validate_file(self, file_path: Union[str, Path]) -> bool:
        """
        Validate file size and type.
        
        Args:
            file_path (Union[str, Path]): Path to the file to validate
            
        Returns:
            bool: True if file is valid, False otherwise
        """
        file_path = Path(file_path)
        
        # Check if file exists
        if not file_path.exists():
            self.logger.error(f"File not found: {file_path}")
            return False
        
        # Check file size
        if file_path.stat().st_size > self.config['max_file_size']:
            self.logger.error(f"File exceeds maximum size of {self.config['max_file_size'] // (1024*1024)}MB")
            return False
        
        # Check file type
        if file_path.suffix.lower() not in self.config['allowed_file_types']:
            self.logger.error(f"File type {file_path.suffix} not allowed")
            return False
        
        return True
    
    def send_dm(self, 
                user_id: str, 
                message: str, 
                formatting: bool = False, 
                file_path: Optional[Union[str, Path]] = None) -> bool:
        """
        Send a direct message to a Slack user.
        
        Args:
            user_id (str): The Slack user ID to send the message to
            message (str): The message to send
            formatting (bool): Whether to enable Slack message formatting
            file_path (Optional[Union[str, Path]]): Path to file to attach
            
        Returns:
            bool: True if message was sent successfully, False otherwise
        """
        try:
            # Validate user_id format
            if not user_id.startswith('U'):
                self.logger.error(f"Invalid user ID format: {user_id}")
                return False
            
            # Handle file attachment if provided
            files = None
            if file_path:
                file_path = Path(file_path)
                if not self._validate_file(file_path):
                    return False
                files = {'file': file_path.open('rb')}
            
            # Send message
            try:
                # First, open a DM channel
                response = self.client.conversations_open(users=[user_id])
                channel_id = response['channel']['id']
                
                # Send the message
                self.client.chat_postMessage(
                    channel=channel_id,
                    text=message,
                    mrkdwn=formatting
                )
                
                # Upload file if provided
                if files:
                    self.client.files_upload(
                        channels=channel_id,
                        file=files['file'],
                        title=file_path.name
                    )
                
                self.logger.info(f"Successfully sent message to {user_id}")
                return True
                
            except SlackApiError as e:
                self.logger.error(f"Failed to send message: {str(e)}")
                return False
                
        except Exception as e:
            self.logger.error(f"Unexpected error: {str(e)}")
            return False
        finally:
            # Clean up file handler if it was opened
            if files:
                files['file'].close()

# Example usage
if __name__ == "__main__":
    # Initialize the messenger
    slack = SlackMessenger()
    
    # Example: Send a simple message
    slack.send_dm(
        user_id="U1234567",
        message="Hello! This is a test message."
    )
    
    # Example: Send a formatted message with a file
    slack.send_dm(
        user_id="U1234567",
        message="*Important*: Please review the attached document.",
        formatting=True,
        file_path="path/to/document.pdf"
    )

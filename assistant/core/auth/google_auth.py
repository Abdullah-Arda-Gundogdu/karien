import os
import json
from pathlib import Path
from typing import Optional
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from assistant.core.logging_config import logger

# Scopes required for the assistant
# We ask for:
# 1. Gmail Readonly (to read emails)
# 2. Calendar (to read/write events)
# 3. Tasks (to read/write tasks)
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks'
]

# Paths relative to this file
CURRENT_DIR = Path(__file__).parent
CREDENTIALS_FILE = CURRENT_DIR / "client_secret_google.json"
TOKEN_FILE = CURRENT_DIR / "token.json"

def get_credentials() -> Optional[Credentials]:
    """
    Obtains valid user credentials from storage.
    If credentials are valid, returns them.
    If they are expired, refreshes them.
    If they are missing, returns None (caller should trigger login).
    """
    creds = None
    if TOKEN_FILE.exists():
        try:
            creds = Credentials.from_authorized_user_file(str(TOKEN_FILE), SCOPES)
        except Exception as e:
            logger.error(f"Failed to load token: {e}")
            # If token is corrupted, we'll return None and force re-login
            return None

    if creds and creds.valid:
        return creds

    if creds and creds.expired and creds.refresh_token:
        try:
            logger.info("Refreshing expired Google token...")
            creds.refresh(Request())
            # Save the refreshed creds
            with open(TOKEN_FILE, 'w') as token:
                token.write(creds.to_json())
            return creds
        except Exception as e:
            logger.error(f"Failed to refresh token: {e}")
            return None
            
    return None

def login() -> Optional[Credentials]:
    """
    Initiates the PKCE login flow for the user.
    This will open a browser window for the user to approve the app.
    """
    if not CREDENTIALS_FILE.exists():
        logger.error(f"Credentials file not found at {CREDENTIALS_FILE}")
        logger.error("Please place your client_secret_google.json in this directory.")
        raise FileNotFoundError(f"Missing client_secret_google.json at {CREDENTIALS_FILE}")

    try:
        logger.info("Starting OAuth2 PKCE Flow...")
        flow = InstalledAppFlow.from_client_secrets_file(
            str(CREDENTIALS_FILE), SCOPES)
        
        # This launches the local server and opens the browser
        # port=0 picks a random available port
        creds = flow.run_local_server(port=0)
        
        # Save the credentials for the next run
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())
            
        logger.info("Google Authentication successful! Token saved.")
        return creds
    except Exception as e:
        logger.error(f"Authentication failed: {e}")
        raise e

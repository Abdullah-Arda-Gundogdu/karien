import datetime
from typing import Any, Dict, List
from googleapiclient.discovery import build
from assistant.core.auth.google_auth import get_credentials
from assistant.core.logging_config import logger

def get_gmail_service():
    """Get authenticated Gmail service."""
    creds = get_credentials()
    if not creds:
        raise Exception("Not logged in. Please authenticate first.")
    return build('gmail', 'v1', credentials=creds)

def get_calendar_service():
    """Get authenticated Calendar service."""
    creds = get_credentials()
    if not creds:
        raise Exception("Not logged in. Please authenticate first.")
    return build('calendar', 'v3', credentials=creds)

def list_recent_emails(limit: int = 5) -> str:
    """
    Reads the user's Gmail inbox.
    
    Args:
        limit (int): Number of emails to retrieve (default 5).
        
    Returns:
        str: A summary of recent emails or error message.
    """
    try:
        service = get_gmail_service()
        results = service.users().messages().list(userId='me', labelIds=['INBOX'], maxResults=limit).execute()
        messages = results.get('messages', [])

        if not messages:
            return "No messages found in inbox."

        summary = []
        for msg in messages:
            txt = service.users().messages().get(userId='me', id=msg['id']).execute()
            payload = txt['payload']
            headers = payload.get("headers", [])
            
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
            snippet = txt.get('snippet', '')
            
            summary.append(f"- From: {sender}\n  Subject: {subject}\n  Snippet: {snippet[:100]}...")
            
        return "\n\n".join(summary)
    
    except Exception as e:
        logger.error(f"Gmail Error: {e}")
        return f"Failed to read emails: {str(e)}"

def add_calendar_event(summary: str, start_time: str, end_time: str = None) -> str:
    """
    Adds an event to the primary Google Calendar.
    
    Args:
        summary (str): Title of the event (e.g., "Meeting with John").
        start_time (str): Start time in ISO format (e.g., "2023-10-27T10:00:00").
        end_time (str, optional): End time in ISO format. If not provided, defaults to 1 hour after start.
        
    Returns:
        str: Confirmation message or error.
    """
    try:
        service = get_calendar_service()
        
        # Parse start time to ensure it's valid ISO 8601
        # Note: Ideally this should handle timezones better, defaulting to local
        start_dt = datetime.datetime.fromisoformat(start_time)
        
        if not end_time:
            end_dt = start_dt + datetime.timedelta(hours=1)
        else:
            end_dt = datetime.datetime.fromisoformat(end_time)
            
        event = {
            'summary': summary,
            'start': {
                'dateTime': start_dt.isoformat(),
                'timeZone': 'UTC', # Should optimally be user's local timezone
            },
            'end': {
                'dateTime': end_dt.isoformat(),
                'timeZone': 'UTC',
            },
        }

        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"Event created: {event.get('htmlLink')}"
        
    except Exception as e:
        logger.error(f"Calendar Error: {e}")
        return f"Failed to create event: {str(e)}"

def get_google_tools_definitions() -> List[Dict[str, Any]]:
    """Returns the OpenAI tool definitions for these functions."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_recent_emails",
                "description": "Read the user's latest emails from Gmail to summarize or find information.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "limit": {
                            "type": "integer",
                            "description": "Number of emails to read (default 5, max 10)",
                            "default": 5
                        }
                    }
                }
            }
        },
        {
            "type": "function",
            "function": {
                "name": "add_calendar_event",
                "description": "Add a new event or meeting to the user's Google Calendar.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "summary": {
                            "type": "string",
                            "description": "Title or description of the event"
                        },
                        "start_time": {
                            "type": "string",
                            "description": "Start time in ISO format (YYYY-MM-DDTHH:MM:SS), e.g. 2024-01-01T14:00:00. Infer the year/date if relative."
                        },
                        "end_time": {
                            "type": "string",
                            "description": "End time in ISO format. Optional, defaults to 1 hour duration."
                        }
                    },
                    "required": ["summary", "start_time"]
                }
            }
        }
    ]

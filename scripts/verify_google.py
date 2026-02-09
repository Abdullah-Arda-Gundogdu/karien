import sys
import os
import datetime

# Ensure the current directory is in the python path
sys.path.append(os.getcwd())

from assistant.mcp.google_mcp import list_recent_emails, add_calendar_event

print("--- Testing Gmail Access ---")
try:
    emails = list_recent_emails(limit=2)
    print(emails)
    print("SUCCESS: Gmail Accessed.")
except Exception as e:
    print(f"FAILURE: Gmail error: {e}")

print("\n--- Testing Calendar Access ---")
try:
    # Schedule for tomorrow at 10am
    tomorrow = datetime.date.today() + datetime.timedelta(days=1)
    start_time = f"{tomorrow}T10:00:00"
    
    print(f"Adding event for {start_time}...")
    result = add_calendar_event(
        summary="Test Event from Karien",
        start_time=start_time
    )
    print(result)
    print("SUCCESS: Calendar Event Added.")
except Exception as e:
    print(f"FAILURE: Calendar error: {e}")

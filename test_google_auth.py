import sys
import os

# Ensure the current directory is in the python path
sys.path.append(os.getcwd())

try:
    from assistant.core.auth.google_auth import login
    print("Attempting to login...")
    creds = login()
    if creds:
        print("SUCCESS: Credentials received and saved!")
    else:
        print("FAILURE: No credentials returned.")
except Exception as e:
    print(f"ERROR: {e}")

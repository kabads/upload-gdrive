import os
import argparse
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from googleapiclient.http import MediaFileUpload

# If modifying these SCOPES, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/drive']
TOKEN_PICKLE_PATH = 'token.json' # Stores the user's access and refresh tokens.
TARGET_FOLDER_NAME = "<YOUR TARGET DIR>"

def get_credentials():
    """Gets user credentials for Google Drive API."""
    creds = None
    credentials_path = os.environ.get('GOOGLE_DRIVE_CREDENTIALS_PATH')
    if not credentials_path:
        print("Error: GOOGLE_DRIVE_CREDENTIALS_PATH environment variable not set.")
        return None
    
    if not os.path.exists(credentials_path):
        print(f"Error: Credentials file not found at {credentials_path}")
        return None

    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first time.
    if os.path.exists(TOKEN_PICKLE_PATH):
        creds = Credentials.from_authorized_user_file(TOKEN_PICKLE_PATH, SCOPES)
    
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
            except Exception as e:
                print(f"Error refreshing token: {e}")
                creds = None # Force re-authentication
        if not creds: # If refresh failed or no token.json
            try:
                flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
                creds = flow.run_local_server(port=0)
            except Exception as e:
                print(f"Error during authentication flow: {e}")
                return None
        # Save the credentials for the next run
        with open(TOKEN_PICKLE_PATH, 'w') as token:
            token.write(creds.to_json())
    return creds

def get_folder_id(service, folder_name):
    """Finds the ID of a folder by its name."""
    try:
        query = f"mimeType='application/vnd.google-apps.folder' and name='{folder_name}' and trashed=false"
        results = service.files().list(q=query, spaces='drive', fields='files(id, name)').execute()
        items = results.get('files', [])
        if not items:
            print(f"Folder '{folder_name}' not found.")
            return None
        # Assuming the first match is the desired one if multiple folders have the same name
        return items[0]['id']
    except HttpError as error:
        print(f"An API error occurred while searching for the folder: {error}")
        return None

def upload_file_to_folder(service, file_path, folder_id):
    """Uploads a file to the specified Google Drive folder."""
    if not os.path.exists(file_path):
        print(f"Error: File not found at {file_path}")
        return None

    file_name = os.path.basename(file_path)
    file_metadata = {
        'name': file_name,
        'parents': [folder_id]
    }
    media = MediaFileUpload(file_path, resumable=True)
    try:
        file = service.files().create(body=file_metadata, media_body=media, fields='id, name').execute()
        print(f"File '{file.get('name')}' uploaded successfully with ID: {file.get('id')}")
        return file.get('id')
    except HttpError as error:
        print(f"An API error occurred during file upload: {error}")
        return None

def main():
    parser = argparse.ArgumentParser(description="Upload a file to a specific Google Drive folder.")
    parser.add_argument("file_path", help="The path to the file to upload.")
    args = parser.parse_args()

    creds = get_credentials()
    if not creds:
        print("Failed to obtain credentials. Exiting.")
        return

    try:
        service = build('drive', 'v3', credentials=creds)
    except Exception as e:
        print(f"Failed to build Drive service: {e}")
        return

    folder_id = get_folder_id(service, TARGET_FOLDER_NAME)
    if not folder_id:
        print(f"Could not find or access folder '{TARGET_FOLDER_NAME}'. Exiting.")
        return

    upload_file_to_folder(service, args.file_path, folder_id)

if __name__ == '__main__':
    main()

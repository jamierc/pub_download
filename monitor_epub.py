#!/usr/bin/env python3
import os
import requests
import smtplib
import subprocess
from email.message import EmailMessage

# --- CONFIGURATION via Environment Variables ---
# Third-party repo details:
THIRD_REPO_OWNER   = os.environ.get("THIRD_REPO_OWNER", "thirdparty")  # e.g. "octocat"
THIRD_REPO_NAME    = os.environ.get("THIRD_REPO_NAME", "repository-name")
THIRD_REPO_FOLDER  = os.environ.get("THIRD_REPO_FOLDER", "path/to/folder")
FILE_EXTENSION     = os.environ.get("FILE_EXTENSION", ".epub")

# GitHub API and token (if needed)
GITHUB_API_URL = "https://api.github.com"
GITHUB_TOKEN   = os.environ.get("GH_TOKEN", "")  # Set in your repo secrets if needed

# Email configuration (set these as secrets in your GitHub Actions repo settings)
SMTP_SERVER    = os.environ.get("SMTP_SERVER", "smtp.example.com")
SMTP_PORT      = int(os.environ.get("SMTP_PORT", 587))
EMAIL_USER     = os.environ.get("EMAIL_USER", "your-email@example.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "your-email-password")
TO_EMAIL       = os.environ.get("TO_EMAIL", "your-email@example.com")

# State file for tracking processed files
STATE_FILE = "processed_files.txt"

def get_headers():
    headers = {"Accept": "application/vnd.github.v3+json"}
    if GITHUB_TOKEN:
        headers["Authorization"] = f"token {GITHUB_TOKEN}"
    return headers

def get_files_in_folder():
    """Call the GitHub API for the third-party repo folder."""
    url = f"{GITHUB_API_URL}/repos/{THIRD_REPO_OWNER}/{THIRD_REPO_NAME}/contents/{THIRD_REPO_FOLDER}"
    response = requests.get(url, headers=get_headers())
    response.raise_for_status()
    files = response.json()
    # Return only files ending with the specified extension (case-insensitive)
    return [f for f in files if f.get("name", "").lower().endswith(FILE_EXTENSION.lower())]

def load_processed_files():
    """Load names of files that have been processed already."""
    processed = set()
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE, "r") as f:
            for line in f:
                processed.add(line.strip())
    return processed

def mark_file_as_processed(file_name):
    """Record that a file has been processed by appending to the state file."""
    with open(STATE_FILE, "a") as f:
        f.write(file_name + "\n")

def download_file(url, local_filename):
    """Download a file from the given URL."""
    print(f"Downloading {local_filename} ...")
    r = requests.get(url)
    r.raise_for_status()
    with open(local_filename, "wb") as f:
        f.write(r.content)

def send_email(file_path, file_name):
    """Email the downloaded file as an attachment."""
    msg = EmailMessage()
    msg["Subject"] = f"New EPUB File: {file_name}"
    msg["From"] = EMAIL_USER
    msg["To"] = TO_EMAIL
    msg.set_content(f"A new EPUB file has been downloaded: {file_name}")
    
    # Read file and attach it
    with open(file_path, "rb") as f:
        file_data = f.read()
    # You can change the mime subtype if necessary
    msg.add_attachment(file_data, maintype="application", subtype="epub", filename=file_name)
    
    print(f"Sending email for {file_name} ...")
    with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as smtp:
        smtp.starttls()  # Secure the connection
        smtp.login(EMAIL_USER, EMAIL_PASSWORD)
        smtp.send_message(msg)
    print("Email sent.")

def main():
    processed_files = load_processed_files()
    try:
        files = get_files_in_folder()
    except Exception as e:
        print(f"Error accessing the folder: {e}")
        return

    for file_info in files:
        file_name = file_info.get("name")
        if file_name in processed_files:
            continue  # Skip already processed files

        download_url = file_info.get("download_url")
        if not download_url:
            print(f"No download URL for {file_name}, skipping.")
            continue

        try:
            download_file(download_url, file_name)
            send_email(file_name, file_name)
        except Exception as e:
            print(f"Error processing {file_name}: {e}")
            continue

        # Mark the file as processed
        mark_file_as_processed(file_name)
        print(f"Processed {file_name}.")

if __name__ == "__main__":
    main()

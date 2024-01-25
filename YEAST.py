#!/usr/bin/env python3

import sys
import os
import subprocess
import requests
import json
import shutil
import tempfile
from urllib.parse import urlparse, parse_qs

# Environment variable setup
os.environ.pop('LD_PRELOAD', None)

# File paths
log_file = os.path.join(os.environ['HOME'], 'Applications/yuzu-ea-revision.log')
backup_log_file = os.path.join(os.environ['HOME'], 'Applications/yuzu-ea-backup-revision.log')
temp_log_file = '/dev/shm/yuzu-ea-temp-revision.log'
appimage_path = os.path.join(os.environ['HOME'], 'Applications/yuzu-ea.AppImage')
backup_path = os.path.join(os.environ['HOME'], 'Applications/yuzu-ea-backup.AppImage')
temp_path = '/dev/shm/yuzu-ea-temp.AppImage'
config_file = os.path.join(os.environ['HOME'], '.config/YEAST.conf')

# Function to display message using Zenity
def display_message(message):
    subprocess.run(['zenity', '--info', '--text', message, '--width=400'])

# Function to prompt for GitHub token using Zenity
def prompt_for_github_token():
    return subprocess.run(['zenity', '--entry', '--title', 'GitHub Token',
                           '--text', 'Enter your GitHub personal access token:',
                           '--hide-text'], capture_output=True, text=True).stdout.strip()

# Function to validate GitHub Access Token
def validate_github_token(token):
    url = "https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    response = requests.get(url, headers={'Authorization': f'token {token}'})
    return "valid" if response.status_code == 200 else "invalid"

# Function to read GitHub Access Token
def read_github_token():
    token = ''
    try:
        with open(config_file, 'r') as file:
            token = file.read().strip()
    except FileNotFoundError:
        pass

    token_status = validate_github_token(token)

    while token_status != "valid":
        token = prompt_for_github_token()
        if not token:
            display_message("No GitHub token provided. To generate a GitHub personal access token, visit https://github.com/settings/tokens")
            continue

        token_status = validate_github_token(token)
        if token_status == "valid":
            with open(config_file, 'w') as file:
                file.write(token)
        else:
            display_message("Invalid GitHub token provided. Please enter a valid token.")

    return token

# Assign the token to a variable
github_token = read_github_token()

def start_loader():
    loader_process = subprocess.Popen(['zenity', '--progress', '--title', 'Searching', '--text', 'Searching for revisions...', '--auto-close', '--no-cancel'],
                                      stdin=subprocess.PIPE, stderr=subprocess.PIPE)
    return loader_process

# Function to fetch and parse releases using GitHub REST API with token
def fetch_releases(url, loader_process):
    response = requests.get(url, headers={'Authorization': f'token {github_token}'})
    if response.status_code != 200:
        # Handle error if the request fails
        loader_process.stdin.write("100\n".encode())
        loader_process.stdin.close()
        loader_process.terminate()
        display_message("Failed to fetch releases. Please check your network connection or GitHub token.")
        return []

    # Assume the response contains a list of tags, each tag being a release
    tags = response.json()
    total_tags = len(tags)

    releases = []
    for i, tag in enumerate(tags):
        release_info = tag['tag_name'].split('EA-')[-1]
        releases.append(release_info)

        # Calculate progress and update the loader bar
        progress = int((i + 1) / total_tags * 100)
        loader_process.stdin.write(f"{progress}\n".encode())
        loader_process.stdin.flush()

    # Close the loader bar when done
    loader_process.stdin.write("100\n".encode())
    loader_process.stdin.close()
    loader_process.wait()

    return releases

# Function to get the URLs for previous and next pages from API response headers with token
def get_pagination_urls(url):
    response = requests.head(url, headers={'Authorization': f'token {github_token}'})
    links = response.headers.get('Link', '')
    prev_url = next_url = None
    for link in links.split(','):
        url, rel = link.split('; ')
        url = url.strip('<> ')
        rel = rel.strip('rel="')
        if rel == 'prev':
            prev_url = url
        elif rel == 'next':
            next_url = url
    return prev_url, next_url

# Function to convert relative URL to absolute URL
def convert_to_absolute_url(relative_url):
    base_url = "https://api.github.com"
    return f"{base_url}{relative_url}"

def search_revision(search_revision):
    graphql_url = "https://api.github.com/graphql"
    query = """
    query($repositoryOwner: String!, $repositoryName: String!) {
        repository(owner: $repositoryOwner, name: $repositoryName) {
            refs(refPrefix: "refs/tags/", first: 100, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
                edges {
                    node {
                        name
                    }
                }
            }
        }
    }
    """
    variables = {
        "repositoryOwner": "pineappleEA",
        "repositoryName": "pineapple-src"
    }
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.post(graphql_url, json={'query': query, 'variables': variables}, headers=headers)

    if response.status_code == 200:
        data = response.json()
        tags = data['data']['repository']['refs']['edges']

        # Convert search_revision to an integer for comparison
        search_revision_number = int(search_revision)

        for edge in tags:
            tag_name = edge['node']['name']
            tag_revision_number = int(tag_name.split('EA-')[-1])  # Extract the revision number
            if tag_revision_number == search_revision_number:
                return tag_name.split('EA-')[-1]
            elif tag_revision_number < search_revision_number:
                return "not_found"  # Stop the search as we've passed the target revision
    return "not_found"

# Function to download with progress
def download_with_progress(url, output_path, revision):
    response = requests.get(url, stream=True)

    if response.status_code != 200:
        display_message("Failed to download the AppImage. Check your internet connection or try again later.")
        exit(1)

    total_size = int(response.headers.get('content-length', 0))
    chunk_size = 1024
    downloaded_size = 0

    # Create a pipe for sending progress to Zenity
    progress_pipe = subprocess.Popen(['zenity', '--progress', '--auto-close',
                                      '--title', 'Downloading', '--text', 'Starting download...'],
                                      stdin=subprocess.PIPE, stderr=subprocess.PIPE)

    with open(output_path, 'wb') as file:
        for data in response.iter_content(chunk_size=chunk_size):
            file.write(data)
            downloaded_size += len(data)
            progress = int((downloaded_size / total_size) * 100)
            # Update Zenity progress bar
            progress_pipe.stdin.write(f"{progress}\n".encode())
            progress_pipe.stdin.flush()

    progress_pipe.stdin.close()
    progress_pipe.wait()

    if progress_pipe.returncode != 0:
        # Handle the case where the download was interrupted or Zenity was closed
        display_message("Download interrupted or cancelled.")
        exit(1)

    os.chmod(output_path, 0o755)
    with open(log_file, 'w') as file:
        file.write(str(revision))
    display_message(f"Download complete. Yuzu EA revision EA-{revision} has been installed.")

# Main loop
def main():
    global current_url, github_token

    current_url = "https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    search_done = False
    revision = None  # Initialize revision to None

    while True:
        if not search_done:
            requested_revision = subprocess.run(['zenity', '--entry', '--title', 'Search for a Specific Revision',
                                                 '--text', 'Enter a revision number to search for (leave blank to browse):'],
                                                 capture_output=True, text=True).stdout.strip()

            if requested_revision:
                found_revision = search_revision(requested_revision)
                if found_revision != "not_found":
                    try:
                        with open(log_file, 'r') as file:
                            installed_tag = file.read().strip()
                    except FileNotFoundError:
                        installed_tag = ""
                    if found_revision == installed_tag:
                        display_message(f"Revision EA-{found_revision} is already installed.")
                        continue
                    revision = found_revision
                    break
                else:
                    display_message(f"Revision EA-{requested_revision} not found.")
                    continue
            search_done = True

        loader_process = start_loader()
        prev_url, next_url = get_pagination_urls(current_url)
        available_tags = fetch_releases(current_url, loader_process)

        if not available_tags:
            display_message("Failed to find available releases. Check your internet connection or GitHub token.")
            continue

        installed_tag = backup_tag = ""
        try:
            with open(log_file, 'r') as file:
                installed_tag = file.read().strip()
            with open(backup_log_file, 'r') as file:
                backup_tag = file.read().strip()
        except FileNotFoundError:
            pass

        menu_options = []
        for tag in available_tags:
            menu_entry = tag
            if tag == installed_tag:
                menu_entry += " (installed)"
            if tag == backup_tag:
                menu_entry += " (backed up)"
            menu_options.append(menu_entry)

        if prev_url:
            menu_options.insert(0, "Previous Page")
        if next_url:
            menu_options.append("Next Page")

        revision_selection = subprocess.run(['zenity', '--list', '--title', 'Select Yuzu EA Revision', '--column', 'Revisions', *menu_options,
                                             '--height=400', '--width=400'], capture_output=True, text=True).stdout.strip()

        if revision_selection == "Previous Page":
            if prev_url:
                current_url = prev_url
            else:
                display_message("No previous page.")
            continue
        elif revision_selection == "Next Page":
            if next_url:
                current_url = next_url
            else:
                display_message("No next page.")
            continue
        elif revision_selection == "":
            display_message("No revision selected.")
            break
        else:
            revision = revision_selection.replace(" (installed)", "").replace(" (backed up)", "")
            if revision == installed_tag:
                display_message(f"Revision EA-{revision} is already installed.")
                continue
            break

    if revision is None or revision in ["Next Page", "Previous Page"]:
        display_message("Invalid selection or no revision selected.")
        return

    if os.path.isfile(appimage_path):
        shutil.copy(appimage_path, temp_path)
        if os.path.isfile(log_file):
            shutil.copy(log_file, temp_log_file)

    skip_download = False
    if os.path.isfile(backup_log_file):
        with open(backup_log_file, 'r') as file:
            backup_revision = file.read().strip()
        if revision == backup_revision:
            if os.path.isfile(backup_path):
                shutil.move(backup_path, appimage_path)
            shutil.move(backup_log_file, log_file)
            skip_download = True
    else:
        skip_download = False

    if skip_download:
        display_message(f"Revision {revision} has been installed from backup.")
    else:
        if not skip_download:
            appimage_url = f"https://github.com/pineappleEA/pineapple-src/releases/download/EA-{revision}/Linux-Yuzu-EA-{revision}.AppImage"
            download_with_progress(appimage_url, appimage_path, revision)

    if os.path.isfile(temp_path):
        shutil.move(temp_path, backup_path)
        if os.path.isfile(temp_log_file):
            shutil.move(temp_log_file, backup_log_file)

    if os.path.isfile(log_file):
        with open(log_file, 'r') as file:
            installed_tag = file.read().strip()
    if os.path.isfile(backup_log_file):
        with open(backup_log_file, 'r') as file:
            backup_tag = file.read().strip()

    subprocess.run(['zenity', '--info', '--text', 'Process completed. Press OK to exit.'])

if __name__ == "__main__":
    main()

#!/usr/bin/env python3

import sys
import os
import subprocess
import requests
import json
import time
import shutil
import tempfile
import hashlib
from urllib.parse import urlparse, parse_qs
import gi

gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib

# Environment variable setup
os.environ.pop('LD_PRELOAD', None)

applications_folder = os.path.join(os.environ['HOME'], 'Applications')

log_file = os.path.join(applications_folder, 'yuzu-ea-revision.log')
backup_log_file = os.path.join(applications_folder, 'yuzu-ea-backup-revision.log')

appimage_path = os.path.join(applications_folder, 'yuzu-ea.AppImage') 
backup_path = os.path.join(applications_folder, 'yuzu-ea-backup.AppImage')

temp_log_file = ('/dev/shm/yuzu-ea-temp-revision.log')
temp_path = ('/dev/shm/yuzu-ea-temp.AppImage')

config_file = os.path.join(os.environ['HOME'], '.config/YEAST.conf')
cache_dir = os.path.join(os.environ['HOME'], 'cache')

# Check if the Applications folder exists, and if not, create it
if not os.path.exists(applications_folder):
    os.makedirs(applications_folder)

def on_treeview_row_activated(treeview, path, column):
    model = treeview.get_model()
    iter = model.get_iter(path)
    selected_row_value = model.get_value(iter, 0)
    # Now, you can use `selected_row_value` which contains the text of the selected row
    # For example, you can print it, store it, or use it in some other part of your program
    print("Selected:", selected_row_value)

def save_to_cache(url, data):
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = os.path.join(cache_dir, f"{url_to_filename(url)}.json")
    with open(cache_file, 'w') as file:
        json.dump({'timestamp': time.time(), 'data': data}, file)

def get_from_cache(url):
    cache_file = os.path.join(cache_dir, f"{url_to_filename(url)}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            cache_content = json.load(file)
        if time.time() - cache_content['timestamp'] < 1 * 6 * 60 * 60:
            return cache_content['data']
    return None

def url_to_filename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def generate_cache_key(query, variables):
    query_string = json.dumps({"query": query, "variables": variables}, sort_keys=True)
    return hashlib.md5(query_string.encode('utf-8')).hexdigest()

# Function to display message using GTK dialog
def display_message(message):
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=message,
    )
    dialog.run()
    dialog.destroy()

# Function to prompt for GitHub token using GTK dialog
def prompt_for_github_token():
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text="Enter your GitHub personal access token:"
    )
    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char("*")
    entry.show()
    dialog.vbox.pack_end(entry, True, True, 0)
    response = dialog.run()
    token = entry.get_text() if response == Gtk.ResponseType.OK else ""
    dialog.destroy()
    return token

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

# Function to start a loader dialog using GTK
def start_loader():
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.NONE,
        text="Searching for revisions..."
    )
    dialog.set_title("Searching")
    dialog.set_default_size(300, 100)

    context = GLib.MainContext.default()
    while GLib.MainContext.iteration(context, False):
        pass

    return dialog

# Function to fetch and parse releases using GitHub REST API with token
def fetch_releases(url, dialog):
    # Check if data is available in cache
    cached_data = get_from_cache(url)
    if cached_data is not None:
        return cached_data

    # If not in cache, fetch data from API
    response = requests.get(url, headers={'Authorization': f'token {github_token}'})
    if response.status_code != 200:
        # Handle error if the request fails
        dialog.destroy()
        display_message("Failed to fetch releases. Please check your network connection or GitHub token.")
        return []

    # Parse the response
    tags = response.json()
    total_tags = len(tags)

    releases = []
    for i, tag in enumerate(tags):
        release_info = tag['tag_name'].split('EA-')[-1]
        releases.append(release_info)

    dialog.destroy()
    # Save the fetched data to cache
    save_to_cache(url, releases)
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
    search_revision_number = int(search_revision)
    end_cursor = None  # Start with no cursor
    has_more_pages = True

    while has_more_pages:
        query, variables = build_graphql_query(end_cursor, search_revision_number)
        cache_key = generate_cache_key(query, variables)
        cached_data = get_from_cache(cache_key)

        if cached_data:
            result, end_cursor = process_cached_data(cached_data, search_revision_number)
        else:
            result, end_cursor = fetch_and_process_data(graphql_url, query, variables, cache_key, search_revision_number)

        if result != "continue" or not end_cursor:
            return result

        # Check if there are more pages to process
        has_more_pages = end_cursor is not None

    # If the loop ends without finding the revision, it means the revision is too low and not found
    return "not_found"

def build_graphql_query(end_cursor, search_revision_number):
    query = """
    query($repositoryOwner: String!, $repositoryName: String!, $after: String) {
        repository(owner: $repositoryOwner, name: $repositoryName) {
            refs(refPrefix: "refs/tags/", first: 100, after: $after, orderBy: {field: TAG_COMMIT_DATE, direction: DESC}) {
                edges {
                    node {
                        name
                    }
                }
                pageInfo {
                    endCursor
                    hasNextPage
                }
            }
        }
    }
    """
    variables = {
        "repositoryOwner": "pineappleEA",
        "repositoryName": "pineapple-src",
        "after": end_cursor
    }
    return query, variables

def fetch_and_process_data(graphql_url, query, variables, cache_key, search_revision_number):
    headers = {"Authorization": f"Bearer {github_token}"}
    response = requests.post(graphql_url, json={'query': query, 'variables': variables}, headers=headers)

    if response.status_code == 200:
        data = response.json()
        save_to_cache(cache_key, data)
        return process_fetched_data(data, search_revision_number)

    return "not_found", None

def process_cached_data(cached_data, search_revision_number):
    tags = cached_data['data']['repository']['refs']['edges']
    pageInfo = cached_data['data']['repository']['refs']['pageInfo']
    end_cursor = pageInfo['endCursor'] if pageInfo['hasNextPage'] else None

    for edge in tags:
        tag_name = edge['node']['name']
        if 'EA-' in tag_name:
            try:
                tag_revision_number = int(tag_name.split('EA-')[-1])
                if tag_revision_number == search_revision_number:
                    return tag_name.split('EA-')[-1], None
                elif tag_revision_number < search_revision_number:
                    return "not_found", None
            except ValueError:
                # Skip if the tag name part is not an integer
                continue

    return "continue", end_cursor

def process_fetched_data(fetched_data, search_revision_number):
    tags = fetched_data['data']['repository']['refs']['edges']
    pageInfo = fetched_data['data']['repository']['refs']['pageInfo']
    end_cursor = pageInfo['endCursor'] if pageInfo['hasNextPage'] else None

    for edge in tags:
        tag_name = edge['node']['name']
        if 'EA-' in tag_name:
            try:
                tag_revision_number = int(tag_name.split('EA-')[-1])
                if tag_revision_number == search_revision_number:
                    return tag_name.split('EA-')[-1], None
                elif tag_revision_number < search_revision_number:
                    return "not_found", None
            except ValueError:
                # Skip if the tag name part is not an integer
                continue

    return "continue", end_cursor

def find_revision_in_tags(tags, search_revision):
    search_revision_number = int(search_revision)
    for edge in tags:
        tag_name = edge['node']['name']
        tag_revision_number = int(tag_name.split('EA-')[-1])
        if tag_revision_number == search_revision_number:
            return tag_name.split('EA-')[-1]
        elif tag_revision_number < search_revision_number:
            return "not_found"
    return "not_found"

def silent_ping(host, count=1):
    try:
        # For Unix/Linux
        subprocess.run(["ping", "-c", str(count), host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        # For Windows
        subprocess.run(["ping", "-n", str(count), host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def download_with_progress(url, output_path, revision):
    response = requests.get(url, stream=True)

    if response.status_code != 200:
        # Ping github.com to check connectivity, suppress output
        silent_ping("github.com")

        if response.status_code == 404:
            display_message("Failed to download the AppImage. The revision might not be found.")
        else:
            display_message("Failed to download the AppImage. Check your internet connection or try again later.")

        # Call main function again instead of exiting
        main()
        return

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
            dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text="Enter a revision number to search for (leave blank to browse):"
            )
            entry = Gtk.Entry()
            entry.show()
            dialog.vbox.pack_end(entry, True, True, 0)
            response = dialog.run()
            requested_revision = entry.get_text() if response == Gtk.ResponseType.OK else None
            dialog.destroy()

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

        # Fetching the releases
        loader_dialog = start_loader()
        prev_url, next_url = get_pagination_urls(current_url)
        available_tags = fetch_releases(current_url, loader_dialog)

        # Checking if releases are available
        if not available_tags:
            display_message("Failed to find available releases. Check your internet connection or GitHub token.")
            continue

        # Preparing the menu options
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

        # Adding pagination options
        if prev_url:
            menu_options.insert(0, "Previous Page")
        if next_url:
            menu_options.append("Next Page")

        # Creating the menu dialog
        liststore = Gtk.ListStore(str)
        for option in menu_options:
            liststore.append([option])

        treeview = Gtk.TreeView(model=liststore)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Revisions", renderer, text=0)
        treeview.append_column(column)
        treeview.connect("row-activated", on_treeview_row_activated)

        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(treeview)

        dialog = Gtk.Dialog(title="Select Yuzu EA Revision", transient_for=None, flags=0)
        dialog.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dialog.vbox.pack_start(scrolled_window, True, True, 0)
        dialog.set_default_size(400, 400)
        dialog.show_all()

        response = dialog.run()

        # Handling dialog response
        if response == Gtk.ResponseType.CANCEL:
            dialog.destroy()
            return
        elif response == Gtk.ResponseType.OK:
            selected_row = treeview.get_selection().get_selected()[1]
            if selected_row is not None:
                revision_selection = liststore[selected_row][0]
                dialog.destroy()

                if revision_selection == "Previous Page":
                    if prev_url:
                        current_url = prev_url
                        continue  # Go back to the start of the loop to reload data
                    else:
                        display_message("No previous page.")
                elif revision_selection == "Next Page":
                    if next_url:
                        current_url = next_url
                        continue  # Go back to the start of the loop to reload data
                    else:
                        display_message("No next page.")
                elif revision_selection == "":
                    display_message("No revision selected.")
                    return
                else:
                    revision = revision_selection.replace(" (installed)", "").replace(" (backed up)", "")
                    if revision == installed_tag:
                        display_message(f"Revision EA-{revision} is already installed.")
                        continue
                    break
            else:
                dialog.destroy()
                continue

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

if __name__ == "__main__":
    main()

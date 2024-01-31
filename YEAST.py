#!/usr/bin/env python3

import threading
from threading import Lock, Thread
from concurrent.futures import ThreadPoolExecutor
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
from gi.repository import Gtk, GLib, Gdk

applications_folder = os.path.join(os.environ['HOME'], 'Applications')

log_file = os.path.join(applications_folder, 'yuzu-ea-revision.log')
backup_log_file = os.path.join(applications_folder, 'yuzu-ea-backup-revision.log')

appimage_path = os.path.join(applications_folder, 'yuzu-ea.AppImage')
backup_path = os.path.join(applications_folder, 'yuzu-ea-backup.AppImage')

temp_log_file = ('/dev/shm/yuzu-ea-temp-revision.log')
temp_path = ('/dev/shm/yuzu-ea-temp.AppImage')

config_dir = os.path.join(os.environ['HOME'], '.config')
cache_dir = os.path.join(os.environ['HOME'], '.cache', 'YEAST')
config_file = os.path.join(config_dir, 'YEAST.conf')

# Global variables for caching
CACHE_EXPIRATION_SECONDS = 50 * 24 * 60 * 60  # 50 days in seconds
cached_pages_count = 0
MAX_PRECACHED_PAGES = 23
memory_cache = {}
memory_cache_lock = threading.Lock()
pre_caching_complete = False
GRAPHQL_URL = "https://api.github.com/graphql"

# Check if the Applications folders exist, and if not, create them
def ensure_directory_exists(directory_path):
    if not os.path.exists(directory_path):
        os.makedirs(directory_path)

ensure_directory_exists(applications_folder)
ensure_directory_exists(cache_dir)
ensure_directory_exists(config_dir)

def on_treeview_row_activated(treeview, path, column):
    model = treeview.get_model()
    iter = model.get_iter(path)
    selected_row_value = model.get_value(iter, 0)
    # Now, you can use `selected_row_value` which contains the text of the selected row
    # For example, you can print it, store it, or use it in some other part of your program
    print("Selected:", selected_row_value)

def pre_cache_graphql_pages():
    global pre_caching_complete
    end_cursor = None
    with ThreadPoolExecutor(max_workers=8) as executor:
        for _ in range(MAX_PRECACHED_PAGES):
            query, variables = build_graphql_query(end_cursor, None)
            cache_key = generate_cache_key(query, variables)

            if not get_from_cache(cache_key):
                future = executor.submit(fetch_and_cache_page, end_cursor)
                end_cursor = future.result()
            else:
                _, end_cursor = process_cached_data(get_from_cache(cache_key), None)

    pre_caching_complete = True  # Indicate that pre-caching is complete

def fetch_and_cache_page(end_cursor):
    query, variables = build_graphql_query(end_cursor, None)
    cache_key = generate_cache_key(query, variables)
    _, new_end_cursor = fetch_and_process_data("https://api.github.com/graphql", query, variables, cache_key, None)
    return new_end_cursor  # Return the end_cursor for the next page

def save_to_memory_cache(cache_key, data):
    with memory_cache_lock:
        memory_cache[cache_key] = data

def get_from_memory_cache(cache_key):
    with memory_cache_lock:
        return memory_cache.get(cache_key)

def save_to_cache(cache_key, data):
    # Save to both memory cache and disk cache
    save_to_memory_cache(cache_key, data)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    with open(cache_file, 'w') as file:
        json.dump({'timestamp': time.time(), 'data': data}, file)

def get_from_cache(cache_key):
    # Try getting from memory cache first
    cached_data = get_from_memory_cache(cache_key)
    if cached_data:
        return cached_data

    # Fall back to disk cache
    cache_file = os.path.join(cache_dir, f"{cache_key}.json")
    if os.path.exists(cache_file):
        with open(cache_file, 'r') as file:
            cache_content = json.load(file)
        if time.time() - cache_content['timestamp'] < CACHE_EXPIRATION_SECONDS:
            save_to_memory_cache(cache_key, cache_content['data'])
            return cache_content['data']

    return None

def url_to_filename(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def generate_cache_key(query, variables):
    query_string = json.dumps({"query": query, "variables": variables}, sort_keys=True)
    return hashlib.md5(query_string.encode('utf-8')).hexdigest()

def clean_up_cache():
    if not os.path.exists(cache_dir):
        return
    for filename in os.listdir(cache_dir):
        filepath = os.path.join(cache_dir, filename)
        if os.path.isfile(filepath):
            file_creation_time = os.path.getmtime(filepath)
            if time.time() - file_creation_time > CACHE_EXPIRATION_SECONDS:
                os.remove(filepath)

# Function to display message using GTK dialog
def display_message(message):
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=message,
    )
    dialog.set_default_size(1280, 80)
    dialog.run()
    dialog.destroy()

def global_key_event_handler(widget, event, dialog, entry):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Return':
        dialog.response(Gtk.ResponseType.OK)
    elif keyname == 'Escape':
        dialog.response(Gtk.ResponseType.CANCEL)
    elif keyname == 'BackSpace':
        entry.set_text(entry.get_text()[:-1])

def github_token_dialog_key_event_handler(widget, event, dialog, entry):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Return':
        dialog.response(Gtk.ResponseType.OK)
    elif keyname == 'Escape':
        dialog.response(Gtk.ResponseType.CANCEL)
    elif keyname == 'BackSpace':
        if not entry.is_focus():
            dialog.response(Gtk.ResponseType.CANCEL)

# Function to prompt for GitHub token using GTK dialog
def prompt_for_github_token():
    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text="Enter your GitHub personal access token:"
    )
    dialog.set_default_size(1280, 80)
    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char("*")
    entry.show()
    dialog.vbox.pack_end(entry, True, True, 0)

    # Connect the new key event handler for the GitHub token dialog
    dialog.connect("key-press-event", github_token_dialog_key_event_handler, dialog, entry)

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
    dialog.set_default_size(1280, 80)

    context = GLib.MainContext.default()
    while GLib.MainContext.iteration(context, False):
        pass

    return dialog

# Function to fetch and parse releases using GitHub REST API with token
def fetch_releases(url, dialog, use_cache=False):  # Accept the argument but don't use it
    response = requests.get(url, headers={'Authorization': f'token {github_token}'})
    if response.status_code != 200:
        dialog.destroy()
        display_message("Failed to fetch releases. Please check your network connection or GitHub token.")
        return []
    tags = response.json()
    releases = [tag['tag_name'].split('EA-')[-1] for tag in tags]
    dialog.destroy()
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
    global pre_caching_complete, GRAPHQL_URL
    search_revision_number = int(search_revision)
    end_cursor = None
    has_more_pages = True
    fetched_from_api = False
    page_count = 0

    while has_more_pages and not fetched_from_api:
        # Wait if pre-caching is not yet complete
        if not pre_caching_complete:
            time.sleep(1)
            continue

        query, variables = build_graphql_query(end_cursor, search_revision_number)
        cache_key = generate_cache_key(query, variables)
        cached_data = get_from_cache(cache_key)

        if cached_data:
            result, end_cursor = process_cached_data(cached_data, search_revision_number)
            if result != "continue":
                return result
        else:
            # Fetch from API if the data is not in the cache
            result, end_cursor = fetch_and_process_data(GRAPHQL_URL, query, variables, cache_key, search_revision_number)
            fetched_from_api = True  # Prevent further caching attempts

            if result != "continue":
                return result

        page_count += 1
        has_more_pages = end_cursor is not None

    # If the desired revision is not found in cache and API, return "not_found"
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
                if search_revision_number is not None:
                    if tag_revision_number == search_revision_number:
                        return tag_name.split('EA-')[-1], None
                    elif tag_revision_number < search_revision_number:
                        return "not_found", None
                # Additional processing can be added here if needed
            except ValueError:
                # Skip if the tag name part is not an integer
                continue

    return "continue", end_cursor

def process_fetched_data(fetched_data, search_revision_number):
    if not fetched_data or 'data' not in fetched_data or 'repository' not in fetched_data['data']:
        return "not_found", None

    tags = fetched_data['data']['repository']['refs']['edges']
    pageInfo = fetched_data['data']['repository']['refs']['pageInfo']
    end_cursor = pageInfo['endCursor'] if pageInfo['hasNextPage'] else None

    if search_revision_number is not None:
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


def create_progress_dialog(title="Downloading", text="Starting download..."):
    dialog = Gtk.Dialog(title)
    dialog.set_default_size(1280, 80)
    progress_bar = Gtk.ProgressBar(show_text=True)
    dialog.vbox.pack_start(progress_bar, True, True, 0)
    dialog.show_all()
    return dialog, progress_bar

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

    dialog, progress_bar = create_progress_dialog()

    with open(output_path, 'wb') as file:
        try:
            for data in response.iter_content(chunk_size=chunk_size):
                file.write(data)
                downloaded_size += len(data)
                progress = downloaded_size / total_size
                GLib.idle_add(progress_bar.set_fraction, progress)
                GLib.idle_add(progress_bar.set_text, f"{int(progress * 100)}%")

                while Gtk.events_pending():
                    Gtk.main_iteration()

                # Check if dialog was closed and stop download if so
                if not dialog.get_visible():
                    raise Exception("Download cancelled by user.")
        except Exception as e:
            dialog.destroy()
            display_message(str(e))
            return

    dialog.destroy()

    os.chmod(output_path, 0o755)
    with open(log_file, 'w') as file:
        file.write(str(revision))
    display_message(f"Download complete. Yuzu EA revision EA-{revision} has been installed.")

# Global key event handler
def global_key_event_handler(widget, event, treeview, liststore, dialog):
    # Only proceed if treeview and liststore are not None
    if treeview is not None and liststore is not None:
        on_key_press_event(event, treeview, liststore, dialog)

# Key press event handler
def on_key_press_event(event, treeview, liststore, dialog):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Left':
        navigate_previous_page(treeview, liststore)
    elif keyname == 'Right':
        navigate_next_page(treeview, liststore)
    elif keyname == 'BackSpace':
        handle_cancel(dialog)
    elif keyname == 'Return':
        handle_ok(treeview, dialog)
    elif keyname == 'Escape':
        sys.exit(0)

# Define handle_ok function
def handle_ok(treeview, dialog):
    model, tree_iter = treeview.get_selection().get_selected()
    if tree_iter is not None:
        selected_row_value = model[tree_iter][0]
        print("OK Selected:", selected_row_value)
        # Implement your logic for OK action here
        dialog.response(Gtk.ResponseType.OK)

# Define handle_cancel function
def handle_cancel(dialog):
    print("Cancel action triggered")
    dialog.response(Gtk.ResponseType.CANCEL)

# Navigation functions: navigate_previous_page and navigate_next_page
def navigate_previous_page(treeview, liststore):
    global prev_url
    if prev_url:
        update_treeview_with_current_page(treeview, liststore, prev_url)

def navigate_next_page(treeview, liststore):
    global next_url
    if next_url:
        update_treeview_with_current_page(treeview, liststore, next_url)

# Update treeview with current page function
def update_treeview_with_current_page(treeview, liststore, url):
    global current_url, prev_url, next_url, installed_tag, backup_tag

    current_url = url  # Update the current URL

    # Create and start the loader dialog
    loader_dialog = start_loader()
    available_tags = fetch_releases(current_url, loader_dialog)

    # Update the prev_url and next_url for pagination
    prev_url, next_url = get_pagination_urls(current_url)

    # Close the loader dialog after fetching releases
    loader_dialog.destroy()

    # Clear existing data in the liststore
    liststore.clear()

    # Check installed and backed up tags
    try:
        with open(log_file, 'r') as file:
            installed_tag = file.read().strip()
        with open(backup_log_file, 'r') as file:
            backup_tag = file.read().strip()
    except FileNotFoundError:
        installed_tag = backup_tag = ""

    # Add Previous Page option if applicable
    if prev_url:
        liststore.append(["Previous Page"])

    # Populate the liststore with new data and add tags
    for tag in available_tags:
        tag_label = tag
        if tag == installed_tag:
            tag_label += " (installed)"
        if tag == backup_tag:
            tag_label += " (backed up)"
        liststore.append([tag_label])

    # Add Next Page option if applicable
    if next_url:
        liststore.append(["Next Page"])

def search_dialog_key_event_handler(widget, event, dialog, entry):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Return':
        dialog.response(Gtk.ResponseType.OK)
    elif keyname == 'Escape':
        dialog.response(Gtk.ResponseType.CANCEL)
    elif keyname == 'BackSpace':
        if not entry.is_focus():
            dialog.response(Gtk.ResponseType.CANCEL)

# Main loop
def main():
    global current_url, github_token, prev_url, next_url

    # Clean up cache at the start of the script
    clean_up_cache()

    # Start pre-caching in a separate thread
    pre_cache_thread = threading.Thread(target=pre_cache_graphql_pages)
    pre_cache_thread.start()

    current_url = "https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    search_done = False
    revision = None  # Initialize revision to None

    while True:
        if not search_done:
            search_dialog = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text="Enter a revision number to search for (leave blank to browse):"
            )
            search_dialog.set_default_size(1280, 80)
            entry = Gtk.Entry()
            entry.show()
            search_dialog.vbox.pack_end(entry, True, True, 0)

            # Connect the specialized key event handler for the search dialog
            search_dialog.connect("key-press-event", search_dialog_key_event_handler, search_dialog, entry)

            response = search_dialog.run()
            if response == Gtk.ResponseType.OK:
                requested_revision = entry.get_text()
            else:
                requested_revision = None
            search_dialog.destroy()

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

        loader_dialog = start_loader()
        prev_url, next_url = get_pagination_urls(current_url)
        available_tags = fetch_releases(current_url, loader_dialog, use_cache=False)
        loader_dialog.destroy()

        if not available_tags:
            display_message("Failed to find available releases. Check your internet connection or GitHub token.")
            continue

        # Sorting the releases in descending order to ensure the latest revision is shown
        available_tags.sort(key=lambda x: int(x), reverse=True)

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
        dialog.set_default_size(80, 800)
        dialog.show_all()

        # Connect the global key event handler and pass the dialog as an argument
        dialog.connect("key-press-event", global_key_event_handler, treeview, liststore, dialog)

        response = dialog.run()

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
                        continue
                    else:
                        display_message("No previous page.")
                elif revision_selection == "Next Page":
                    if next_url:
                        current_url = next_url
                        continue
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
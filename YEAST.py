#!/usr/bin/env python3

import threading
import subprocess
import requests
import json
import time
import shutil
import os
import hashlib
from urllib.parse import urlparse, parse_qs
from concurrent.futures import ThreadPoolExecutor
import gi
gi.require_version("Gtk", "3.0")
from gi.repository import Gtk, GLib, Gdk

# Abbreviations and common string extractions
app_fldr = os.path.join(os.environ['HOME'], 'Applications')
log_f = os.path.join(app_fldr, 'yuzu-ea-revision.log')
bkup_log_f = os.path.join(app_fldr, 'yuzu-ea-backup-revision.log')
appimg_pth = os.path.join(app_fldr, 'yuzu-ea.AppImage')
bkup_pth = os.path.join(app_fldr, 'yuzu-ea-backup.AppImage')
temp_log_f = '/dev/shm/yuzu-ea-temp-revision.log'
temp_pth = '/dev/shm/yuzu-ea-temp.AppImage'
cfg_dir = os.path.join(os.environ['HOME'], '.config')
cache_dir = os.path.join(os.environ['HOME'], '.cache', 'YEAST')
cfg_f = os.path.join(cfg_dir, 'YEAST.conf')
cache_exp = 50 * 24 * 60 * 60  # 50 days in seconds
cached_pg_cnt = 0
max_precached = 23
mem_cache = {}
mem_cache_lock = threading.Lock()
pre_caching_done = False
graphql_url = "https://api.github.com/graphql"

def ensure_dir_exists(dir_pth):
    if not os.path.exists(dir_pth):
        os.makedirs(dir_pth)

ensure_dir_exists(app_fldr)
ensure_dir_exists(cache_dir)
ensure_dir_exists(cfg_dir)

def on_tv_row_act(tv, pth, col):
    model = tv.get_model()
    it = model.get_iter(pth)
    sel_row_val = model.get_value(it, 0)
    print("Selected:", sel_row_val)

def pre_cache_gql_pages():
    global pre_caching_done, graphql_url
    e_cursor = None
    with ThreadPoolExecutor(max_workers=8) as exec:
        for _ in range(max_precached):
            qry, vars = build_gql_qry(e_cursor, None)
            cache_k = gen_cache_key(qry, vars)

            if not get_from_cache(cache_k):
                fut = exec.submit(fetch_and_cache_pg, e_cursor)
                e_cursor = fut.result()
            else:
                _, e_cursor = proc_cached_data(get_from_cache(cache_k), None)

    pre_caching_done = True

def fetch_and_cache_pg(e_cursor):
    qry, vars = build_gql_qry(e_cursor, None)
    cache_k = gen_cache_key(qry, vars)
    _, new_e_cursor = fetch_and_proc_data(graphql_url, qry, vars, cache_k, None)
    return new_e_cursor

def save_to_mem_cache(cache_k, data):
    with mem_cache_lock:
        mem_cache[cache_k] = data

def get_from_mem_cache(cache_k):
    with mem_cache_lock:
        return mem_cache.get(cache_k)

def save_to_cache(cache_k, data):
    save_to_mem_cache(cache_k, data)
    if not os.path.exists(cache_dir):
        os.makedirs(cache_dir)
    cache_f = os.path.join(cache_dir, f"{cache_k}.json")
    with open(cache_f, 'w') as f:
        json.dump({'timestamp': time.time(), 'data': data}, f)

def get_from_cache(cache_k):
    cached_data = get_from_mem_cache(cache_k)
    if cached_data:
        return cached_data
    cache_f = os.path.join(cache_dir, f"{cache_k}.json")
    if os.path.exists(cache_f):
        with open(cache_f, 'r') as f:
            cache_cont = json.load(f)
        if time.time() - cache_cont['timestamp'] < cache_exp:
            save_to_mem_cache(cache_k, cache_cont['data'])
            return cache_cont['data']
    return None

def url_to_fn(url):
    return hashlib.md5(url.encode('utf-8')).hexdigest()

def gen_cache_key(qry, vars):
    qry_str = json.dumps({"query": qry, "variables": vars}, sort_keys=True)
    return hashlib.md5(qry_str.encode('utf-8')).hexdigest()

def clean_up_cache():
    if not os.path.exists(cache_dir):
        return
    for fn in os.listdir(cache_dir):
        fpath = os.path.join(cache_dir, fn)
        if os.path.isfile(fpath):
            f_ctime = os.path.getmtime(fpath)
            if time.time() - f_ctime > cache_exp:
                os.remove(fpath)

def disp_msg(msg):
    dlg = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.OK,
        text=msg,
    )
    dlg.set_default_size(1280, 80)
    dlg.run()
    dlg.destroy()

def gk_event_hdlr(widget, event, dlg, entry):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Return':
        dlg.response(Gtk.ResponseType.OK)
    elif keyname == 'Escape':
        dlg.response(Gtk.ResponseType.CANCEL)
    elif keyname == 'BackSpace':
        entry.set_text(entry.get_text()[:-1])

def gh_token_dlg_k_event_hdlr(widget, event, dlg, entry):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Return':
        dlg.response(Gtk.ResponseType.OK)
    elif keyname == 'Escape':
        dlg.response(Gtk.ResponseType.CANCEL)
    elif keyname == 'BackSpace':
        if not entry.is_focus():
            dlg.response(Gtk.ResponseType.CANCEL)

def prompt_for_gh_token():
    dlg = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.OK_CANCEL,
        text="Enter your GitHub personal access token:"
    )
    dlg.set_default_size(1280, 80)
    entry = Gtk.Entry()
    entry.set_visibility(False)
    entry.set_invisible_char("*")
    entry.show()
    dlg.vbox.pack_end(entry, True, True, 0)
    dlg.connect("key-press-event", gh_token_dlg_k_event_hdlr, dlg, entry)
    response = dlg.run()
    token = entry.get_text() if response == Gtk.ResponseType.OK else ""
    dlg.destroy()
    return token

def validate_gh_token(token):
    url = "https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    resp = requests.get(url, headers={'Authorization': f'token {token}'})
    return "valid" if resp.status_code == 200 else "invalid"

def read_gh_token():
    token = ''
    try:
        with open(cfg_f, 'r') as f:
            token = f.read().strip()
    except FileNotFoundError:
        pass

    try:
        token_status = validate_gh_token(token)
        while token_status != "valid":
            token = prompt_for_gh_token()
            if not token:
                disp_msg("No GitHub token provided. To generate a GitHub personal access token, visit https://github.com/settings/tokens")
                continue
            token_status = validate_gh_token(token)
            if token_status == "valid":
                with open(cfg_f, 'w') as f:
                    f.write(token)
            else:
                disp_msg("Invalid GitHub token provided. Please enter a valid token.")
    except requests.exceptions.ConnectionError:
        disp_msg("Failed to connect to GitHub to validate the token. Please check your internet connection.")
    except Exception as e:
        disp_msg(f"An unexpected error occurred: {e}")

    return token

gh_token = read_gh_token()

def start_loader():
    dlg = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.INFO,
        buttons=Gtk.ButtonsType.NONE,
        text="Searching for revisions..."
    )
    dlg.set_title("Searching")
    dlg.set_default_size(1280, 80)
    ctxt = GLib.MainContext.default()
    while GLib.MainContext.iteration(ctxt, False):
        pass
    return dlg

def fetch_releases(url, dlg, use_cache=False):
    try:
        resp = requests.get(url, headers={'Authorization': f'token {gh_token}'})
        if resp.status_code != 200:
            dlg.destroy()
            disp_msg("Failed to fetch releases. Please check your network connection or GitHub token.")
            return []
        tags = resp.json()
        releases = [tag['tag_name'].split('EA-')[-1] for tag in tags]
        dlg.destroy()
        return releases
    except requests.exceptions.ConnectionError:
        dlg.destroy()
        disp_msg("Failed to connect to GitHub. Please check your internet connection.")
        return []
    except Exception as e:
        dlg.destroy()
        disp_msg(f"An unexpected error occurred while fetching releases: {e}")
        return []

def get_pagination_urls(url):
    resp = requests.head(url, headers={'Authorization': f'token {gh_token}'})
    links = resp.headers.get('Link', '')
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

def conv_to_abs_url(rel_url):
    base_url = "https://api.github.com"
    return f"{base_url}{rel_url}"

def search_rev(search_rev):
    global pre_caching_done, graphql_url
    search_rev_num = int(search_rev)
    e_cursor = None
    has_more_pgs = True
    fetched_from_api = False
    pg_cnt = 0
    while has_more_pgs and not fetched_from_api:
        if not pre_caching_done:
            time.sleep(1)
            continue
        qry, vars = build_gql_qry(e_cursor, search_rev_num)
        cache_k = gen_cache_key(qry, vars)
        cached_data = get_from_cache(cache_k)
        if cached_data:
            result, e_cursor = proc_cached_data(cached_data, search_rev_num)
            if result != "continue":
                return result
        else:
            result, e_cursor = fetch_and_proc_data(graphql_url, qry, vars, cache_k, search_rev_num)
            fetched_from_api = True
            if result != "continue":
                return result
        pg_cnt += 1
        has_more_pgs = e_cursor is not None
    return "not_found"

def build_gql_qry(e_cursor, search_rev_num):
    qry = """
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
    vars = {
        "repositoryOwner": "pineappleEA",
        "repositoryName": "pineapple-src",
        "after": e_cursor
    }
    return qry, vars

def fetch_and_proc_data(gql_url, qry, vars, cache_k, search_rev_num):
    hdrs = {"Authorization": f"Bearer {gh_token}"}
    resp = requests.post(gql_url, json={'query': qry, 'variables': vars}, headers=hdrs)
    if resp.status_code == 200:
        data = resp.json()
        save_to_cache(cache_k, data)
        return proc_fetched_data(data, search_rev_num)
    return "not_found", None

def proc_cached_data(cached_data, search_rev_num):
    tags = cached_data['data']['repository']['refs']['edges']
    pageInfo = cached_data['data']['repository']['refs']['pageInfo']
    e_cursor = pageInfo['endCursor'] if pageInfo['hasNextPage'] else None
    for edge in tags:
        tag_name = edge['node']['name']
        if 'EA-' in tag_name:
            try:
                tag_rev_num = int(tag_name.split('EA-')[-1])
                if search_rev_num is not None:
                    if tag_rev_num == search_rev_num:
                        return tag_name.split('EA-')[-1], None
                    elif tag_rev_num < search_rev_num:
                        return "not_found", None
            except ValueError:
                continue
    return "continue", e_cursor

def proc_fetched_data(fetched_data, search_rev_num):
    if not fetched_data or 'data' not in fetched_data or 'repository' not in fetched_data['data']:
        return "not_found", None
    tags = fetched_data['data']['repository']['refs']['edges']
    pageInfo = fetched_data['data']['repository']['refs']['pageInfo']
    e_cursor = pageInfo['endCursor'] if pageInfo['hasNextPage'] else None
    if search_rev_num is not None:
        for edge in tags:
            tag_name = edge['node']['name']
            if 'EA-' in tag_name:
                try:
                    tag_rev_num = int(tag_name.split('EA-')[-1])
                    if tag_rev_num == search_rev_num:
                        return tag_name.split('EA-')[-1], None
                    elif tag_rev_num < search_rev_num:
                        return "not_found", None
                except ValueError:
                    continue
    return "continue", e_cursor

def find_rev_in_tags(tags, search_rev):
    search_rev_num = int(search_rev)
    for edge in tags:
        tag_name = edge['node']['name']
        tag_rev_num = int(tag_name.split('EA-')[-1])
        if tag_rev_num == search_rev_num:
            return tag_name.split('EA-')[-1]
        elif tag_rev_num < search_rev_num:
            return "not_found"
    return "not_found"

def silent_ping(host, count=1):
    try:
        subprocess.run(["ping", "-c", str(count), host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except FileNotFoundError:
        subprocess.run(["ping", "-n", str(count), host], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

def create_prog_dlg(title="Downloading", text="Starting download..."):
    dlg = Gtk.Dialog(title)
    dlg.set_default_size(1280, 80)
    prog_bar = Gtk.ProgressBar(show_text=True)
    dlg.vbox.pack_start(prog_bar, True, True, 0)
    dlg.show_all()
    return dlg, prog_bar

def dl_with_prog(url, out_pth, rev):
    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        silent_ping("github.com")
        if resp.status_code == 404:
            disp_msg("Failed to download the AppImage. The revision might not be found.")
        else:
            disp_msg("Failed to download the AppImage. Check your internet connection or try again later.")
        main()
        return
    total_size = int(resp.headers.get('content-length', 0))
    chunk_size = 1024
    dl_size = 0
    dlg, prog_bar = create_prog_dlg()
    with open(out_pth, 'wb') as f:
        try:
            for data in resp.iter_content(chunk_size=chunk_size):
                f.write(data)
                dl_size += len(data)
                progress = dl_size / total_size
                GLib.idle_add(prog_bar.set_fraction, progress)
                GLib.idle_add(prog_bar.set_text, f"{int(progress * 100)}%")
                while Gtk.events_pending():
                    Gtk.main_iteration()
                if not dlg.get_visible():
                    raise Exception("Download cancelled by user.")
        except Exception as e:
            dlg.destroy()
            disp_msg(str(e))
            return
    dlg.destroy()
    os.chmod(out_pth, 0o755)
    with open(log_f, 'w') as f:
        f.write(str(rev))
    disp_msg(f"Download complete. Yuzu EA-{rev} has been installed.")

def gk_event_hdlr(widget, event, tv, lststore, dlg):
    if tv is not None and lststore is not None:
        on_k_press_event(event, tv, lststore, dlg)

def on_k_press_event(event, tv, lststore, dlg):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Left':
        nav_prev_pg(tv, lststore)
    elif keyname == 'Right':
        nav_next_pg(tv, lststore)
    elif keyname == 'BackSpace':
        handle_cancel(dlg)
    elif keyname == 'Return':
        handle_ok(tv, dlg)
    elif keyname == 'Escape':
        sys.exit(0)

def handle_ok(tv, dlg):
    model, tree_it = tv.get_selection().get_selected()
    if tree_it is not None:
        sel_row_val = model[tree_it][0]
        print("OK Selected:", sel_row_val)
        dlg.response(Gtk.ResponseType.OK)

def handle_cancel(dlg):
    print("Cancel action triggered")
    dlg.response(Gtk.ResponseType.CANCEL)

def nav_prev_pg(tv, lststore):
    global prev_url
    if prev_url:
        update_tv_with_curr_pg(tv, lststore, prev_url)

def nav_next_pg(tv, lststore):
    global next_url
    if next_url:
        update_tv_with_curr_pg(tv, lststore, next_url)

def update_tv_with_curr_pg(tv, lststore, url):
    global current_url, prev_url, next_url, installed_tag, bkup_tag
    current_url = url
    loader_dlg = start_loader()
    available_tags = fetch_releases(current_url, loader_dlg)
    prev_url, next_url = get_pagination_urls(current_url)
    loader_dlg.destroy()
    lststore.clear()
    try:
        with open(log_f, 'r') as f:
            installed_tag = f.read().strip()
        with open(bkup_log_f, 'r') as f:
            bkup_tag = f.read().strip()
    except FileNotFoundError:
        installed_tag = bkup_tag = ""
    if prev_url:
        lststore.append(["Previous Page"])
    for tag in available_tags:
        tag_label = tag
        if tag == installed_tag:
            tag_label += " (installed)"
        if tag == bkup_tag:
            tag_label += " (backed up)"
        lststore.append([tag_label])
    if next_url:
        lststore.append(["Next Page"])

def search_dlg_k_event_hdlr(widget, event, dlg, entry):
    keyname = Gdk.keyval_name(event.keyval)
    if keyname == 'Return':
        dlg.response(Gtk.ResponseType.OK)
    elif keyname == 'Escape':
        dlg.response(Gtk.ResponseType.CANCEL)
    elif keyname == 'BackSpace':
        if not entry.is_focus():
            dlg.response(Gtk.ResponseType.CANCEL)

def ping_github():
    try:
        subprocess.run(["ping", "-c", "1", "github.com"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=True)
        return True
    except subprocess.CalledProcessError:
        return False

def read_revision_number(log_path):
    try:
        with open(log_path, 'r') as f:
            return f.read().strip()
    except FileNotFoundError:
        return "unknown"  # Return a placeholder if the log file doesn't exist

def prompt_revert_to_backup():
    # Read the currently installed and backed up revision numbers
    installed_rev = read_revision_number(log_f)
    backed_up_rev = read_revision_number(bkup_log_f)

    # Construct the message text with the revision information
    message_text = f"Currently installed revision: {installed_rev}\n" \
                   f"Backup revision: {backed_up_rev}\n\n" \
                   "Would you like to revert to the backup installation of Yuzu EA?"

    dialog = Gtk.MessageDialog(
        transient_for=None,
        flags=0,
        message_type=Gtk.MessageType.QUESTION,
        buttons=Gtk.ButtonsType.YES_NO,
        text=message_text
    )
    response = dialog.run()
    dialog.destroy()
    return response == Gtk.ResponseType.YES

def revert_to_backup():
    if os.path.exists(appimg_pth) and os.path.exists(bkup_pth):
        shutil.move(appimg_pth, temp_pth)  # Move current AppImage to a temporary location
        shutil.move(bkup_pth, appimg_pth)  # Move backup AppImage to the current location
        shutil.move(temp_pth, bkup_pth)  # Move the temporary AppImage to the backup location

        if os.path.exists(log_f) and os.path.exists(bkup_log_f):
            shutil.move(log_f, temp_log_f)  # Move current log to a temporary location
            shutil.move(bkup_log_f, log_f)  # Move backup log to the current log's location
            shutil.move(temp_log_f, bkup_log_f)  # Move the temporary log to the backup log's location

        print("Successfully reverted to the backup installation of Yuzu EA.")
    else:
        print("Backup installation not found.")

# Main loop
def main():
    global current_url, gh_token, prev_url, next_url

    if not ping_github():
        # If GitHub is not reachable, ask the user if they want to revert to the backup
        if prompt_revert_to_backup():
            revert_to_backup()
            return  # Stop execution after reverting to backup

    clean_up_cache()
    pre_cache_thread = threading.Thread(target=pre_cache_gql_pages)
    pre_cache_thread.start()
    current_url = "https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    search_done = False
    rev = None
    while True:
        if not search_done:
            search_dlg = Gtk.MessageDialog(
                transient_for=None,
                flags=0,
                message_type=Gtk.MessageType.QUESTION,
                buttons=Gtk.ButtonsType.OK_CANCEL,
                text="Enter a revision number to search for (leave blank to browse):"
            )
            search_dlg.set_default_size(1280, 80)
            entry = Gtk.Entry()
            entry.show()
            search_dlg.vbox.pack_end(entry, True, True, 0)
            search_dlg.connect("key-press-event", search_dlg_k_event_hdlr, search_dlg, entry)
            response = search_dlg.run()
            if response == Gtk.ResponseType.OK:
                req_rev = entry.get_text()
            else:
                req_rev = None
            search_dlg.destroy()
            if req_rev:
                found_rev = search_rev(req_rev)
                if found_rev != "not_found":
                    try:
                        with open(log_f, 'r') as f:
                            installed_tag = f.read().strip()
                    except FileNotFoundError:
                        installed_tag = ""
                    if found_rev == installed_tag:
                        disp_msg(f"Revision EA-{found_rev} is already installed.")
                        continue
                    rev = found_rev
                    break
                else:
                    disp_msg(f"Revision EA-{req_rev} not found.")
                    continue
            search_done = True
        loader_dlg = start_loader()
        prev_url, next_url = get_pagination_urls(current_url)
        available_tags = fetch_releases(current_url, loader_dlg, use_cache=False)
        loader_dlg.destroy()
        if not available_tags:
            disp_msg("Failed to find available releases. Check your internet connection or GitHub token.")
            continue
        available_tags.sort(key=lambda x: int(x), reverse=True)
        installed_tag = bkup_tag = ""
        try:
            with open(log_f, 'r') as f:
                installed_tag = f.read().strip()
            with open(bkup_log_f, 'r') as f:
                bkup_tag = f.read().strip()
        except FileNotFoundError:
            pass
        menu_opts = []
        for tag in available_tags:
            menu_entry = tag
            if tag == installed_tag:
                menu_entry += " (installed)"
            if tag == bkup_tag:
                menu_entry += " (backed up)"
            menu_opts.append(menu_entry)
        if prev_url:
            menu_opts.insert(0, "Previous Page")
        if next_url:
            menu_opts.append("Next Page")
        lststore = Gtk.ListStore(str)
        for option in menu_opts:
            lststore.append([option])
        tv = Gtk.TreeView(model=lststore)
        renderer = Gtk.CellRendererText()
        column = Gtk.TreeViewColumn("Revisions", renderer, text=0)
        tv.append_column(column)
        tv.connect("row-activated", on_tv_row_act)
        scrolled_window = Gtk.ScrolledWindow()
        scrolled_window.set_hexpand(True)
        scrolled_window.set_vexpand(True)
        scrolled_window.add(tv)
        dlg = Gtk.Dialog(title="Select Yuzu EA Revision", transient_for=None, flags=0)
        dlg.add_buttons(Gtk.STOCK_OK, Gtk.ResponseType.OK, Gtk.STOCK_CANCEL, Gtk.ResponseType.CANCEL)
        dlg.vbox.pack_start(scrolled_window, True, True, 0)
        dlg.set_default_size(80, 800)
        dlg.show_all()
        dlg.connect("key-press-event", gk_event_hdlr, tv, lststore, dlg)
        response = dlg.run()
        if response == Gtk.ResponseType.CANCEL:
            dlg.destroy()
            return
        elif response == Gtk.ResponseType.OK:
            selected_row = tv.get_selection().get_selected()[1]
            if selected_row is not None:
                rev_selection = lststore[selected_row][0]
                dlg.destroy()
                if rev_selection == "Previous Page":
                    if prev_url:
                        current_url = prev_url
                        continue
                    else:
                        disp_msg("No previous page.")
                elif rev_selection == "Next Page":
                    if next_url:
                        current_url = next_url
                        continue
                    else:
                        disp_msg("No next page.")
                elif rev_selection == "":
                    disp_msg("No revision selected.")
                    return
                else:
                    rev = rev_selection.replace(" (installed)", "").replace(" (backed up)", "")
                    if rev == installed_tag:
                        disp_msg(f"Revision EA-{rev} is already installed.")
                        continue
                    break
            else:
                dlg.destroy()
                continue
    if os.path.isfile(appimg_pth):
        shutil.copy(appimg_pth, temp_pth)
        if os.path.isfile(log_f):
            shutil.copy(log_f, temp_log_f)
    skip_dl = False
    if os.path.isfile(bkup_log_f):
        with open(bkup_log_f, 'r') as f:
            bkup_rev = f.read().strip()
        if rev == bkup_rev:
            if os.path.isfile(bkup_pth):
                shutil.move(bkup_pth, appimg_pth)
            shutil.move(bkup_log_f, log_f)
            skip_dl = True
    else:
        skip_dl = False
    if skip_dl:
        disp_msg(f"Revision {rev} has been installed from backup.")
    else:
        if not skip_dl:
            appimg_url = f"https://github.com/pineappleEA/pineapple-src/releases/download/EA-{rev}/Linux-Yuzu-EA-{rev}.AppImage"
            dl_with_prog(appimg_url, appimg_pth, rev)
    if os.path.isfile(temp_pth):
        shutil.move(temp_pth, bkup_pth)
        if os.path.isfile(temp_log_f):
            shutil.move(temp_log_f, bkup_log_f)
    if os.path.isfile(log_f):
        with open(log_f, 'r') as f:
            installed_tag = f.read().strip()
    if os.path.isfile(bkup_log_f):
        with open(bkup_log_f, 'r') as f:
            bkup_tag = f.read().strip()

if __name__ == "__main__":
    main()

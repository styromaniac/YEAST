#!/bin/bash

unset LD_PRELOAD

log_file="$HOME/Applications/yuzu-ea-revision.log"
backup_log_file="$HOME/Applications/yuzu-ea-backup-revision.log"
temp_log_file="/dev/shm/yuzu-ea-temp-revision.log"
appimage_path="$HOME/Applications/yuzu-ea.AppImage"
backup_path="$HOME/Applications/yuzu-ea-backup.AppImage"
temp_path="/dev/shm/yuzu-ea-temp.AppImage"

# Check if whiptail is installed
if ! command -v whiptail >/dev/null 2>&1; then
    echo "whiptail is not installed. Please install it to use this script."
    exit 1
fi

# Function to fetch and parse releases from GitHub
fetch_releases() {
    local url=$1
    curl -s -Z --max-time 60 "$url" | grep -oP 'EA-\K\d+' | sort -ur
}

# Function to get the URLs for previous and next pages
get_pagination_urls() {
    local url=$1
    prev_url=$(curl -s "$url" | grep -oP '(?<=href=")[^"]*(?=">Previous)' | head -1)
    next_url=$(curl -s "$url" | grep -oP '(?<=href=")[^"]*(?=">Next)' | head -1)
}

# Initial URL
current_url="https://github.com/pineappleEA/pineapple-src/releases"
get_pagination_urls "$current_url"
available_tags=$(fetch_releases "$current_url")

# Check for available releases
if [ -z "$available_tags" ]; then
    echo "Failed to find available releases."
    read -p "Press Enter to exit..."
    exit 1
fi

# Check the currently installed and backed up versions
installed_tag=""
backup_tag=""
if [ -f "$log_file" ]; then
    installed_tag=$(cat "$log_file")
    echo "Currently installed version: EA-$installed_tag"
fi
if [ -f "$backup_log_file" ]; then
    backup_tag=$(cat "$backup_log_file")
    echo "Currently backed up version: EA-$backup_tag"
fi

# Menu creation logic with pagination
while true; do
    MENU_OPTIONS=()
    for tag in $available_tags; do
        menu_entry="$tag"
        [ "$tag" == "$installed_tag" ] && menu_entry+=" (installed)"
        [ "$tag" == "$backup_tag" ] && menu_entry+=" (backed up)"
        MENU_OPTIONS+=("$menu_entry" "")
    done

    [ -n "$next_url" ] && MENU_OPTIONS+=("Next Page" "")
    [ -n "$prev_url" ] && MENU_OPTIONS+=("Previous Page" "")

    revision=$(whiptail --title "Select Yuzu EA Revision" --menu "Choose a revision to install:" 20 78 12 "${MENU_OPTIONS[@]}" 3>&1 1>&2 2>&3)

    exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Operation cancelled."
        exit 0
    elif [ "$revision" == "Next Page" ]; then
        current_url="https://github.com$next_url"
        get_pagination_urls "$current_url"
        available_tags=$(fetch_releases "$current_url")
    elif [ "$revision" == "Previous Page" ]; then
        current_url="https://github.com$prev_url"
        get_pagination_urls "$current_url"
        available_tags=$(fetch_releases "$current_url")
    else
        # Remove additional text for processing
        revision=${revision// \(installed\)/}
        revision=${revision// \(backed up\)/}
        [ "$revision" == "$installed_tag" ] && echo "Revision EA-$revision is already installed." && continue
        break
    fi
done

# Check if a valid revision is selected
if [[ "$revision" == "Next Page" ]] || [[ "$revision" == "Previous Page" ]]; then
    echo "Invalid selection."
    exit 1
fi

echo "Selected revision: EA-$revision has been installed from backup."

# Rotate the revisions: installed -> temp -> backup -> installed
if [ -f "$appimage_path" ]; then
    cp "$appimage_path" "$temp_path"
    [ -f "$log_file" ] && cp "$log_file" "$temp_log_file"
fi

# Restore from backup if needed
skip_download=false
if [ -f "$backup_log_file" ]; then
    backup_revision=$(cat "$backup_log_file")
    if [ "$revision" = "$backup_revision" ]; then
        [ -f "$backup_path" ] && mv "$backup_path" "$appimage_path"
        mv "$backup_log_file" "$log_file"
        skip_download=true
    fi
else
    skip_download=false
fi

# Download the AppImage only if not skipping
if [ "$skip_download" = false ]; then
    appimage_url="https://github.com/pineappleEA/pineapple-src/releases/download/EA-${revision}/Linux-Yuzu-EA-${revision}.AppImage"
    echo "Downloading revision EA-$revision from $appimage_url..."
    curl -L --max-time 60 "$appimage_url" -o "$appimage_path" --create-dirs

    if [ ! -f "$appimage_path" ]; then
        echo "Failed to download the AppImage. Check your internet connection or try again later."
        exit 1
    fi

    chmod +x "$appimage_path"
    echo "$revision" > "$log_file"  # Update log file after download
    echo "Download complete. Yuzu EA revision EA-$revision has been installed."
fi

# Rotate the backup
if [ -f "$temp_path" ]; then
    mv "$temp_path" "$backup_path"
    [ -f "$temp_log_file" ] && mv "$temp_log_file" "$backup_log_file"
fi

read -p "Press Enter to exit..."

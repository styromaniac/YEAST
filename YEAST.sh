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

# Fetch all available release tags from the GitHub page and remove duplicates
available_tags=$(curl -s -Z --max-time 60 https://github.com/pineappleEA/pineapple-src/releases | grep -oP 'EA-\K\d+' | sort -ur)

if [ -z "$available_tags" ]; then
    echo "Failed to find available releases."
    read -p "Press enter to exit..."
    exit 1
fi

# Check the currently installed version
if [ -f "$log_file" ]; then
    installed_tag=$(cat "$log_file")
    echo "Currently installed version: EA-$installed_tag"
else
    installed_tag=""
fi

# Create a menu using whiptail
MENU_OPTIONS=()
for tag in $available_tags; do
    if [ "$tag" != "$installed_tag" ]; then
        MENU_OPTIONS+=("$tag" "")
    fi
done

revision=$(whiptail --title "Select Yuzu EA Revision" --menu "Choose a revision to install:" 20 78 10 "${MENU_OPTIONS[@]}" 3>&1 1>&2 2>&3)

exit_status=$?
if [ $exit_status -ne 0 ] || [ -z "$revision" ]; then
    echo "Operation cancelled or no revision selected."
    exit 0
fi

echo "Selected revision: EA-$revision"

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

read -p "Press enter to exit..."

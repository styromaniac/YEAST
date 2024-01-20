#!/bin/bash

unset LD_PRELOAD

log_file="$HOME/Applications/yuzu-ea-revision.log"
backup_log_file="$HOME/Applications/yuzu-ea-backup-revision.log"
temp_log_file="/dev/shm/yuzu-ea-temp-revision.log"
appimage_path="$HOME/Applications/yuzu-ea.AppImage"
backup_path="$HOME/Applications/yuzu-ea-backup.AppImage"
temp_path="/dev/shm/yuzu-ea-temp.AppImage"
config_file="$HOME/.config/YEAST.conf"

# Function to read GitHub Access Token
read_github_token() {
    if [ -f "$config_file" ]; then
        cat "$config_file"
    else
        echo "GitHub access token file not found."
        exit 1
    fi
}

# Assign the token to a variable
github_token=$(read_github_token)

# Function to fetch and parse releases using GitHub REST API with token
fetch_releases() {
    local url=$1
    curl -s -H "Authorization: token $github_token" "$url" | jq -r '.[].tag_name' | grep -oP 'EA-\K\d+' | sort -ur
}

# Function to get the URLs for previous and next pages from API response headers with token
get_pagination_urls() {
    local url=$1
    response=$(curl -s -I -H "Authorization: token $github_token" "$url")
    prev_url=$(echo "$response" | grep -oP '(?<=<)[^>]*(?=>; rel="prev")' | head -1)
    next_url=$(echo "$response" | grep -oP '(?<=<)[^>]*(?=>; rel="next")' | head -1)
}

# Function to convert relative URL to absolute URL
convert_to_absolute_url() {
    local base_url="https://api.github.com"
    local relative_url=$1
    echo "$base_url${relative_url}"
}

search_revision() {
    local search_revision=$1
    local search_url="https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    local found_revision="not_found"

    while [ -n "$search_url" ]; do
        get_pagination_urls "$search_url"
        local tags=$(fetch_releases "$search_url")
        for tag in $tags; do
            if [ "$tag" == "$search_revision" ]; then
                found_revision=$tag
                echo "$found_revision"
                return
            fi
            # Check if the current tag is less than the search_revision
            if [ "$tag" -lt "$search_revision" ]; then
                echo "$found_revision"
                return
            fi
        done
        search_url="$next_url"
    done
    echo "$found_revision"
}

# Main loop
while true; do
    # Initial URL for GitHub API
    current_url="https://api.github.com/repos/pineappleEA/pineapple-src/releases"
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
        echo "Past installed version: EA-$installed_tag"
    fi
    if [ -f "$backup_log_file" ]; then
        backup_tag=$(cat "$backup_log_file")
        echo "Past backed up version: EA-$backup_tag"
    fi

    # Determine the terminal size
    terminal_height=$(tput lines)
    terminal_width=$(tput cols)

    # Calculate the menu size
    menu_height=$((terminal_height - 3))
    menu_width=$((terminal_width - 4))
    menu_list_height=$((menu_height - 8))

    # Add Whiptail Input Box with matching window parameters
    requested_revision=$(whiptail --title "Revision Input" --inputbox "Type a desired revision number to install or leave blank to browse revisions." $menu_height $menu_width 3>&1 1>&2 2>&3)

    # Process the Input
    if [ -n "$requested_revision" ]; then
        found_revision=$(search_revision "$requested_revision")
        if [ "$found_revision" != "not_found" ]; then
            revision=$found_revision
            echo "Found revision: EA-$revision"
            break  # Exit the while loop if the revision is found
        else
            echo "Revision EA-$requested_revision not found. Reloading..."
            # Continue the loop to reload the menu
            continue
        fi
    fi

    # Menu creation logic with pagination
    MENU_OPTIONS=()
    DEFAULT_ITEM=""

    # Add 'Previous Page' option at the top if available
    if [ -n "$prev_url" ]; then
        MENU_OPTIONS+=("Previous Page" "")
    fi

    # Add available tags (revisions)
    for tag in $available_tags; do
        menu_entry="$tag"
        [ "$tag" == "$installed_tag" ] && menu_entry+=" (installed)"
        [ "$tag" == "$backup_tag" ] && menu_entry+=" (backed up)"
        MENU_OPTIONS+=("$menu_entry" "")
        # Set the latest revision as the default item
        [ -z "$DEFAULT_ITEM" ] && DEFAULT_ITEM="$menu_entry"
    done

    # Add 'Next Page' option at the bottom if available
    if [ -n "$next_url" ]; then
        MENU_OPTIONS+=("Next Page" "")
    fi

    # Launch the whiptail menu with the default item set to the latest revision
    revision=$(whiptail --title "Select Yuzu EA Revision" --menu "Choose a revision to install:" $menu_height $menu_width $menu_list_height "${MENU_OPTIONS[@]}" --default-item "$DEFAULT_ITEM" 3>&1 1>&2 2>&3)

    exit_status=$?
    if [ $exit_status -ne 0 ]; then
        echo "Operation cancelled or an error occurred."
        exit $exit_status
    fi

    if [ "$revision" == "Next Page" ]; then
        if [ -n "$next_url" ]; then
            echo "Fetching from: $next_url"
            get_pagination_urls "$next_url"
            available_tags=$(fetch_releases "$next_url")
            current_url="$next_url"  # Update current URL
        else
            echo "No more pages."
        fi
    elif [ "$revision" == "Previous Page" ]; then
        if [ -n "$prev_url" ]; then
            echo "Fetching from: $prev_url"
            get_pagination_urls "$prev_url"
            available_tags=$(fetch_releases "$prev_url")
            current_url="$prev_url"  # Update current URL
        else
            echo "No previous page."
        fi
    else
        # Remove additional text for processing
        revision=${revision// \(installed\)/}
        revision=${revision// \(backed up\)/}
        [ "$revision" == "$installed_tag" ] && echo "Revision EA-$revision is already installed." && continue
        break
    fi

    # Re-generate MENU_OPTIONS for the new page
    get_pagination_urls "$current_url"
    available_tags=$(fetch_releases "$current_url")
done

# Check if a valid revision is selected
if [[ "$revision" == "Next Page" ]] || [[ "$revision" == "Previous Page" ]]; then
    echo "Invalid selection."
    exit 1
fi

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

if [ "$skip_download" = true ]; then
    echo "Revision $revision has been installed from backup."
else
    # Download the AppImage
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

# Final prompt before exiting the script
read -r -p "Press Enter to exit..." key

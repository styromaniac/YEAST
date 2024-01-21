#!/bin/env bash

unset LD_PRELOAD

log_file="$HOME/Applications/yuzu-ea-revision.log"
backup_log_file="$HOME/Applications/yuzu-ea-backup-revision.log"
temp_log_file="/dev/shm/yuzu-ea-temp-revision.log"
appimage_path="$HOME/Applications/yuzu-ea.AppImage"
backup_path="$HOME/Applications/yuzu-ea-backup.AppImage"
temp_path="/dev/shm/yuzu-ea-temp.AppImage"
config_file="$HOME/.config/YEAST.conf"

# Function to display message using Zenity
display_message() {
    local message=$1
    zenity --info --text="$message" --width=400
}

# Function to prompt for GitHub token using Zenity
prompt_for_github_token() {
    zenity --entry --title="GitHub Token" --text="Enter your GitHub personal access token:" --hide-text
}

# Function to validate GitHub Access Token
validate_github_token() {
    local token=$1
    local url="https://api.github.com/repos/pineappleEA/pineapple-src/releases"
    if curl -s -o /dev/null -w "%{http_code}" -H "Authorization: token $token" "$url" | grep -q "200"; then
        echo "valid"
    else
        echo "invalid"
    fi
}

# Function to read GitHub Access Token
read_github_token() {
    token=$(cat "$config_file" 2>/dev/null)
    token_status=$(validate_github_token "$token")

    while [ "$token_status" != "valid" ]; do
        token=$(prompt_for_github_token)
        if [ -z "$token" ]; then
            display_message "No GitHub token provided. To generate a GitHub personal access token, visit https://github.com/settings/tokens"
            continue
        fi

        token_status=$(validate_github_token "$token")
        if [ "$token_status" = "valid" ]; then
            echo "$token" > "$config_file"
        else
            display_message "Invalid GitHub token provided. Please enter a valid token."
        fi
    done

    echo "$token"
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
            if [ "$tag" -lt "$search_revision" ]; then
                echo "$found_revision"
                return
            fi
        done
        search_url="$next_url"
    done
    echo "$found_revision"
}

# Function to download the AppImage with progress displayed through Zenity
download_with_progress() {
    local url=$1
    local output_path=$2

    # Use curl to download the file with progress information
    # and pipe it to Zenity's progress dialog
    curl -L "$url" -o "$output_path" --progress-bar 2>&1 | \
    stdbuf -oL tr '\r' '\n' | \
    stdbuf -oL awk 'BEGIN {ORS=" "} {if(NR % 2 == 1) print int($0)}' | \
    zenity --progress --title="Downloading" --text="Downloading Yuzu EA revision EA-$revision..." --auto-close --width=400 --percentage=0

    if [ ! -f "$output_path" ]; then
        display_message "Failed to download the AppImage. Check your internet connection or try again later."
        exit 1
    fi

    chmod +x "$output_path"
    echo "$revision" > "$log_file"
    display_message "Download complete. Yuzu EA revision EA-$revision has been installed."
}

# Main loop
search_done=false
while true; do
    if ! $search_done; then
        requested_revision=$(zenity --entry --title="Search for a Specific Revision" --text="Enter a revision number to search for (leave blank to browse):")
        if [ -n "$requested_revision" ]; then
            found_revision=$(search_revision "$requested_revision")
            if [ "$found_revision" != "not_found" ]; then
                installed_tag=$(cat "$log_file")
                if [ "$found_revision" == "$installed_tag" ]; then
                    display_message "Revision EA-$found_revision is already installed."
                    continue
                fi
                revision=$found_revision
                break
            else
                display_message "Revision EA-$requested_revision not found."
                continue
            fi
        fi
        search_done=true
    fi

    current_url="${current_url:-https://api.github.com/repos/pineappleEA/pineapple-src/releases}"
    get_pagination_urls "$current_url"
    available_tags=$(fetch_releases "$current_url")

    if [ -z "$available_tags" ]; then
        display_message "Failed to find available releases. Did you not enter an auth token?"
        exit 1
    fi

    installed_tag=""
    backup_tag=""
    if [ -f "$log_file" ]; then
        installed_tag=$(cat "$log_file")
    fi
    if [ -f "$backup_log_file" ]; then
        backup_tag=$(cat "$backup_log_file")
    fi

    MENU_OPTIONS=()

    for tag in $available_tags; do
        menu_entry="$tag"
        [ "$tag" == "$installed_tag" ] && menu_entry+=" (installed)"
        [ "$tag" == "$backup_tag" ] && menu_entry+=" (backed up)"
        MENU_OPTIONS+=("$menu_entry")
    done

    if [ -n "$prev_url" ]; then
        MENU_OPTIONS=("Previous Page" "${MENU_OPTIONS[@]}")
    fi
    if [ -n "$next_url" ]; then
        MENU_OPTIONS+=("Next Page")
    fi

    revision_selection=$(zenity --list --title="Select Yuzu EA Revision" --column="Revisions" "${MENU_OPTIONS[@]}" --height=400 --width=400)

    case "$revision_selection" in
        "Previous Page")
            if [ -n "$prev_url" ]; then
                current_url="$prev_url"
            else
                display_message "No previous page."
            fi
            ;;
        "Next Page")
            if [ -n "$next_url" ]; then
                current_url="$next_url"
            else
                display_message "No next page."
            fi
            ;;
        "")
            display_message "No revision selected."
            exit 1
            ;;
        *)
            revision=${revision_selection// \(installed\)/}
            revision=${revision// \(backed up\)/}
            [ "$revision" == "$installed_tag" ] && display_message "Revision EA-$revision is already installed." && continue
            break
            ;;
    esac
done

if [[ "$revision" == "Next Page" ]] || [[ "$revision" == "Previous Page" ]]; then
    display_message "Invalid selection."
    exit 1
fi

if [ -f "$appimage_path" ]; then
    cp "$appimage_path" "$temp_path"
    [ -f "$log_file" ] && cp "$log_file" "$temp_log_file"
fi

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
    display_message "Revision $revision has been installed from backup."
else
    appimage_url="https://github.com/pineappleEA/pineapple-src/releases/download/EA-${revision}/Linux-Yuzu-EA-${revision}.AppImage"
    download_with_progress "$appimage_url" "$appimage_path"
fi

if [ -f "$temp_path" ]; then
    mv "$temp_path" "$backup_path"
    [ -f "$temp_log_file" ] && mv "$temp_log_file" "$backup_log_file"
fi

installed_tag=""
backup_tag=""
if [ -f "$log_file" ]; then
    installed_tag=$(cat "$log_file")
fi
if [ -f "$backup_log_file" ]; then
    backup_tag=$(cat "$backup_log_file")
fi

zenity --info --text="Process completed. Press OK to exit."

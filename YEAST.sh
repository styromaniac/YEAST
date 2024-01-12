#!/bin/bash

unset LD_PRELOAD

log_file="$HOME/Applications/yuzu-ea-revision.log"
appimage_path="$HOME/Applications/yuzu-ea.AppImage"

# Fetch the latest release tag from the GitHub page
latest_tag=$(curl -s https://github.com/pineappleEA/pineapple-src/releases | grep -oP 'EA-\K\d+' | head -n 1)

if [ -z "$latest_tag" ]; then
    echo "Failed to find the latest release tag."
    while true; do
    sleep 1
    done

fi

# Check if the latest version is already installed
if [ -f "$log_file" ]; then
    installed_tag=$(cat "$log_file")
    if [ "$latest_tag" = "$installed_tag" ]; then
        echo "The latest version (EA-$latest_tag) is already installed."
        while true; do
        sleep 1
        done
    fi
fi

# Construct the download URL
appimage_url="https://github.com/pineappleEA/pineapple-src/releases/download/EA-${latest_tag}/Linux-Yuzu-EA-${latest_tag}.AppImage"

# Download the AppImage, overwriting if it exists
curl -L "$appimage_url" -o "$appimage_path" --create-dirs

# Make the file executable
chmod +x "$appimage_path"

# Update the log file
echo "$latest_tag" > "$log_file"

echo "Download complete. Yuzu EA revision EA-$latest_tag has been installed."

mpg123 chime.mp3 > /dev/null 2>&1

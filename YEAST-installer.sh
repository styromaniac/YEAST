#!/bin/bash

# Archive name
archive_name="YEAST.zip"

# Internal file names
script_name="YEAST.sh"
icon_name="YEAST.png"

# Temporary directory
temp_dir="/tmp/YEAST-install"

# Install locations
script_install_location="$HOME/Applications/$script_name"

# Desktop file locations
desktop_file="$HOME/.local/share/applications/$script_name.desktop"
icon_install_location="$HOME/.local/share/applications/$icon_name"

# Install script
mkdir -p "$HOME/Applications"
cp "$temp_dir/$script_name" "$script_install_location"
chmod +x "$script_install_location"

# Install icon
mkdir -p "$HOME/.local/share/applications"
cp "$temp_dir/$icon_name" "$icon_install_location"

# Create .desktop file
echo "[Desktop Entry]
Name=YEAST
Comment=Install the latest Yuzu EA AppImage
Exec=$script_install_location
Icon=$icon_name
Categories=Game;Emulator;" > "$desktop_file"

# Clean up
rm -r "$temp_dir"

echo "Installed to $script_install_location"
echo "Desktop file created: $desktop_file"

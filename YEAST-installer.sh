#!/bin/bash

# Set fallback directory values if unset
if [ -z "$XDG_DATA_HOME" ]; then
  XDG_DATA_HOME="$HOME/.local/share"
fi

if [ -z "$XDG_CONFIG_HOME" ]; then
  XDG_CONFIG_HOME="$HOME/Applications"
fi

# Script config
script_name="YEAST.py"
icon_name="YEAST-logo.png"

# Install directories
install_dir="$XDG_CONFIG_HOME"
icon_dir="$XDG_DATA_HOME/icons"
desktop_dir="$XDG_DATA_HOME/applications"

# Functions
copy_file() {
  cp "$1" "$2" || {
    echo "Failed copying $1"
    exit 1
  }
}

create_desktop_entry() {
  cat <<EOF > "$1"
[Desktop Entry]
Name=YEAST
Exec=$install_dir/$script_name
Icon=YEAST
Type=Application
Categories=Game;
EOF
}

# Main install
mkdir -p "$install_dir"
copy_file "$script_name" "$install_dir"
chmod +x "$install_dir/$script_name"

mkdir -p "$icon_dir"
copy_file "$icon_name" "$icon_dir"

create_desktop_entry "$desktop_dir/$script_name.desktop"

echo "Installed to $install_dir/$script_name"


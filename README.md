<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-capsule.png" width="256">

# yuzu early access software tracker (YEAST)

A robust, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros using [pineappleEA's pineapple-src releases](https://github.com/pineappleEA/pineapple-src/releases). This app complements (instead of competes with) EmuDeck. The purpose of this script is to save the user's time by being more easily accessible, convenient, logical, and informative. It is usable through Gaming Mode In SteamOS 3, Bazzite, ChimeraOS, HoloISO, and Nobara Linux Steam Deck Edition.

YEAST will not redownload the same revision of yuzu-ea.AppImage that's already installed. The prior installed revision will be backed up and will be sourced from its backup file instead of redownloaded if it's reinstalled, saving bandwidth.

## Install System Dependencies
First, install the necessary system dependencies for your specific Linux distribution:

### Debian/Ubuntu (apt)
```bash
sudo apt-get update
sudo apt-get install python3-gi python3-gi-cairo gir1.2-gtk-3.0
```

### Fedora (dnf)
```bash
sudo dnf install python3-gobject python3-cairo-gobject gtk3
```

### Arch Linux (pacman)
```bash
sudo pacman -Syu
sudo pacman -S python-gobject python-cairo gtk3
```

### openSUSE (zypper)
```bash
sudo zypper refresh
sudo zypper install python3-gobject python3-gobject-cairo gtk3
```

### CentOS (yum)
For CentOS 7:
```bash
sudo yum install python3-gobject python3-cairo-gobject gtk3
```
For CentOS 8, you might need to enable EPEL and PowerTools repositories, and the package names could be slightly different. 

### Gentoo (emerge)
```bash
sudo emerge --sync
sudo emerge dev-python/pygobject:3 x11-libs/gtk+:3
```

## Install pip
Next, install `pip`, the Python package manager, on your distribution:

### Debian/Ubuntu (apt)
```bash
sudo apt-get update
sudo apt-get install python3-pip
```

### Fedora (dnf)
```bash
sudo dnf install python3-pip
```

### Arch Linux (pacman)
```bash
sudo pacman -Syu
sudo pacman -S python-pip
```

### openSUSE (zypper)
```bash
sudo zypper refresh
sudo zypper install python3-pip
```

### CentOS (yum)
For CentOS 7:
```bash
sudo yum install epel-release
sudo yum install python-pip
```
For CentOS 8:
```bash
sudo dnf install python3-pip
```

### Gentoo (emerge)
```bash
sudo emerge --sync
sudo emerge dev-python/pip
```

Note:
- For CentOS 7, the EPEL (Extra Packages for Enterprise Linux) repository is required to install `pip`.
- CentOS 8 and newer versions use `dnf` as the default package manager.
- Always ensure your system's package index is up-to-date (`update`, `refresh`, `--sync`) before installing new packages.

## Install Python3 Modules
Finally, use `pip` to install the required Python modules:

```
pip install requests PyGObject
```
## Building a Binary
To build a binary for YEAST.py on Linux, you can use a tool like `PyInstaller` which freezes Python applications into stand-alone executables. This process involves a few steps: installing PyInstaller, preparing your script, and then using PyInstaller to create the binary. Here's a step-by-step guide:

### 1. Install PyInstaller
First, you need to install PyInstaller. It's recommended to do this in a virtual environment to avoid conflicts with system packages.

```bash
# Create a virtual environment (optional but recommended)
python3 -m venv yeast_env
source yeast_env/bin/activate

# Install PyInstaller
pip install pyinstaller
```

### 2. Prepare Your Script
Make sure the script `YEAST.py` is ready and tested. All dependencies should be correctly imported in the script.

### 3. Build the Binary
Navigate to the directory where `YEAST.py` is located and run PyInstaller:

```bash
cd /path/to/your/script
pyinstaller --onefile YEAST.py
```

The `--onefile` option tells PyInstaller to pack everything into a single executable file. After the process completes, you'll find the binary in the `dist` directory.

### 4. Test the Binary
It's important to test the binary to make sure it runs correctly:

```bash
./dist/YEAST
```

### Notes:
- YEAST-installer.sh already exists to install YEAST.py and is recommended for simple installation.
- The binary built with PyInstaller is specific to the OS and architecture you build it on. If you build it on Ubuntu, it's meant for Ubuntu systems, and similarly for other distributions.
- If YEASTlication depends on non-Python files (like images, data files, etc.), you need to tell PyInstaller to include these files. Check PyInstaller's documentation for more on this.
- Building a binary does not always guarantee the same performance or behavior as running the script directly with Python. Be sure to thoroughly test the binary on the target system.

### Optional: Creating a Desktop Entry
If you want to integrate YEAST with the Linux desktop environments, you can create a `.desktop` file:

```ini
[Desktop Entry]
Name=YEAST
Exec=/path/to/dist/YEAST
Icon=/path/to/YEAST-icon.png
Type=Application
Categories=Utility;
```

Replace `/path/to/dist/YEAST` with the actual path to the executable and `/path/to/YEAST-icon.png` with the path to an icon of your choice. This file should be placed in `~/.local/share/applications/` or `/usr/share/applications/` for system-wide availability.

By following these steps, you should be able to create a binary for YEAST that can be distributed and run on Linux systems.

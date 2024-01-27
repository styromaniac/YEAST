<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-capsule.png" width="256">

# yuzu early access software tracker (YEAST)

A robust, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros. This app complements (instead of competes with) EmuDeck. The purpose of this script is to save the user's time by being more easily accessible, convenient, logical, and informative. It is usable through Gaming Mode In SteamOS 3, Bazzite, ChimeraOS, HoloISO, and Nobara Linux.

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

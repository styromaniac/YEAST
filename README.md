<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-capsule.png" width="256">

# yuzu early access software tracker

A robust, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros. This app complements (instead of competes with) EmuDeck. The purpose of this script is to save the user's time by being more easily accessible, convenient, logical and informative. It is usable through Gaming Mode.

YEAST will not redownload the same revision of yuzu-ea.AppImage that's already installed. The prior installed revision will be backed up and will be sourced from its backup file instead of redownloaded if it's reinstalled, saving bandwidth.

To install `pip`, the Python package manager, on various Linux distributions, you can use the following commands based on the specific package manager each distribution uses:

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
- CentOS 8 and newer versions use `dnf` (Dandified YUM) as the default package manager, which is more or less similar to `yum`.
- In most cases, the command `python3-pip` will install `pip` for Python 3.
- Always ensure your system's package index is up-to-date (`update`, `refresh`, `--sync`) before installing new packages.
```
pip install requests PyGObject
```
Here's how you can install the required packages on different Linux distributions using their respective package managers:

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

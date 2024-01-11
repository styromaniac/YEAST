<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-hero.png" width="256">

yuzu early access software tracker

A simple, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros without additional dependencies.

Instructions after installing YEAST and adding it to Steam:

In Steam under YEAST > Properties > Shortcut...

Change TARGET to:
```
/bin/bash
```
Change START IN to:
```
/bin
```
Change LAUNCH OPTIONS to:
```
-e "$HOME/.config/apps/YEAST.sh"
```

YEAST needs to first be launched without Steam if yuzu-ea.AppImage isn't preinstalled to /home/Applications, then it can update yuzu-ea.AppImage via Steam.

Launching YEAST will appear to do nothing, but it's actually working in the background. When the job is complete, you'll be returned back to the YEAST page in your library if YEAST is launched via Steam.

YEAST will not redownload the same version of yuzu-ea.AppImage that's already installed, thus using minimal bandwidth while checking for newer releases.

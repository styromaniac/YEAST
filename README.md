<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-hero.png" width="256">

yuzu early access software tracker

Simple, code-readable yuzu early access installer/updater for SteamOS and other Linux distros.

Instructions to Add YEAST to Steam
After installation...
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
Launching YEAST will appear to do nothing, but it's actually working in the background. When the job is complete, you'll be returned back to the YEAST page in your library.

YEAST will not redownload the same version of yuzu-ea.AppImage that's already installed, thus using minimal bandwidth while checking for newer releases.

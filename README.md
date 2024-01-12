<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-hero.png" width="256">

# yuzu early access software tracker

A simple, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros without additional dependencies.

## Instructions...

1. [Install Black Box.](https://flathub.org/apps/com.raggesilver.BlackBox)

2.Add Black Box to Steam.

3. Append to the end LAUNCH OPTIONS:
```
--command $HOME/Applications/YEAST.sh
```

YEAST will not redownload the same version of yuzu-ea.AppImage that's already installed, thus using minimal bandwidth while checking for newer releases.

<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-capsule.png" width="256">

# yuzu early access software tracker

A simple, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros without additional dependencies, except for the Black Box Flatpak. This app complements (instead of competes with) EmuDeck.

## Instructions...

1. [Install Black Box.](https://flathub.org/apps/com.raggesilver.BlackBox)

2. Add Black Box to Steam.

3. Navigate to Black Box in your Steam library.

4. Press/click on the gear icon.

5. Change the name to YEAST.

6. Append to the end of the LAUNCH OPTIONS string:
```
 --command $HOME/Applications/YEAST.sh
```
Now you can apply the custom artwork using the [Decky Loader](https://decky.xyz/) plugin SteamGridDB (only on SteamOS 3+) or by right-clicking where the artwork is absent.

YEAST will not redownload the same revision of yuzu-ea.AppImage that's already installed. The prior installed revision will be backed up and will be sourced from its backup file instead of redownloaded if it's reinstalled, saving bandwidth.

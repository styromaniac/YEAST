<img src="https://raw.githubusercontent.com/styromaniac/YEAST/main/YEAST-capsule.png" width="256">

# yuzu early access software tracker

A simple, code-readable yuzu early access installer/updater for Steam on SteamOS and other Linux distros without additional dependencies.

## Instructions...

1. [Install Black Box.](https://flathub.org/apps/com.raggesilver.BlackBox)

2. Add Black Box to Steam.

3. Navigate to Black Box in your Steam library.

4. Press/click on the gear icon.

5. Change the name to YEAST

6. Append to the end of the LAUNCH OPTIONS string:
```
--command $HOME/Applications/YEAST.sh
```
You might hear a chime sound when YEAST-installer.sh or YEAST.sh succeeds.

Now you can apply the custom artwork using the [Decky Loader](https://decky.xyz/) plugin SteamGridDB (only on SteamOS 3+) or right-clicking where the artwork is absent.

YEAST will not redownload the same version of yuzu-ea.AppImage that's already installed, thus using minimal bandwidth while checking for newer releases.

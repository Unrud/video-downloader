# Video Downloader

Download videos from websites with an easy-to-use interface.
Provides the following features:

  * Convert videos to MP3
  * Supports password-protected and private videos
  * Download single videos or whole playlists
  * Automatically selects a video format based on your quality demands

Based on [youtube-dl](https://yt-dl.org).

## Installation

  * [Flatpak](https://flathub.org/apps/details/com.github.unrud.VideoDownloader)
  * [Snap](https://snapcraft.io/video-downloader)
  * [Fedora](https://src.fedoraproject.org/rpms/video-downloader): `sudo dnf install video-downloader`

## Screenshots

![screenshot 1](https://raw.githubusercontent.com/Unrud/video-downloader/master/screenshots/1.png)

![screenshot 2](https://raw.githubusercontent.com/Unrud/video-downloader/master/screenshots/2.png)

![screenshot 3](https://raw.githubusercontent.com/Unrud/video-downloader/master/screenshots/3.png)

## Hidden configuration options

The behavior of the program can be tweaked with GSettings.

### Download folder

Paths can either be absolute or start with `~`, `xdg-desktop`, `xdg-download`,
`xdg-templates`, `xdg-publicshare`, `xdg-documents`, `xdg-music`, `xdg-pictures` or `xdg-videos`.

The default is `xdg-download/VideoDownloader`.

#### Flatpak
In the following example, the download location is being changed to `~/Videos/VideoDownloader` or `xdg-videos/VideoDownloader`.
```
flatpak run --command=gsettings com.github.unrud.VideoDownloader set com.github.unrud.VideoDownloader download-folder 'xdg-videos/VideoDownloader'
```
Remember to also give the flatpak the necessary filesystem permissions. This can be done through the command-line or through _Flatseal_.  If you used `xdg-videos/VideoDownloader` as the download folder in the previous command, remember to use that in the following command as well. Using `~/Videos/VideoDownloader` may cause an error.
```
flatpak override com.github.unrud.VideoDownloader --filesystem=xdg-videos/VideoDownloader:create
```
`:create` tells flatpak to make a new folder called `VideoDownloader` in `~/Videos` if it doesn't already exist.

#### Snap

```
snap run --shell video-downloader -c 'gsettings "$@"' '' set com.github.unrud.VideoDownloader download-folder '~/VideoDownloader'
```

### Prefer MPEG

Prefer MPEG videos instead of free formats when both are available at the same
resolution and frame rate.

The default is `false`.

#### Flatpak

```
flatpak run --command=gsettings com.github.unrud.VideoDownloader set com.github.unrud.VideoDownloader prefer-mpeg true
```

#### Snap

```
snap run --shell video-downloader -c 'gsettings "$@"' '' set com.github.unrud.VideoDownloader prefer-mpeg true
```

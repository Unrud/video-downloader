# Video Downloader

Download videos from websites with an easy-to-use interface.
Provides the following features:

  * Convert videos to MP3
  * Supports password-protected and private videos
  * Download single videos or whole playlists
  * Automatically selects a video format based on your quality demands

Based on [youtube-dl](http://ytdl-org.github.io/youtube-dl/).

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

```
flatpak run --command=gsettings com.github.unrud.VideoDownloader set com.github.unrud.VideoDownloader download-folder '~/VideoDownloader'
```

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

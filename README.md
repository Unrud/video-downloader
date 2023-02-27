[![Translation status](https://hosted.weblate.org/widgets/video-downloader/-/gui/svg-badge.svg)](https://hosted.weblate.org/engage/video-downloader/)

# Video Downloader

Download videos from websites with an easy-to-use interface.
Provides the following features:

  * Convert videos to MP3
  * Supports password-protected and private videos
  * Download single videos or whole playlists
  * Automatically selects a video format based on your quality demands

Based on [yt-dlp](https://github.com/yt-dlp/yt-dlp).

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

Grant filesystem access to the sandboxed app:
```
flatpak override --user --filesystem='~/VideoDownloader:create' com.github.unrud.VideoDownloader
```

#### Snap

```
snap run --shell video-downloader -c 'gsettings "$@"' '' set com.github.unrud.VideoDownloader download-folder '~/VideoDownloader'
```

### Automatic Subtitles

List of additional automatic subtitles to download. The entry `all` matches all languages.

The default is `[]`.

#### Flatpak

```
flatpak run --command=gsettings com.github.unrud.VideoDownloader set com.github.unrud.VideoDownloader automatic-subtitles "['de','en']"
```

#### Snap

```
snap run --shell video-downloader -c 'gsettings "$@"' '' set com.github.unrud.VideoDownloader automatic-subtitles "['de','en']"
```

## Debug

To display messages from **yt-dlp** run program with the environment variable `G_MESSAGES_DEBUG=yt-dlp`.

To display information about GOBject references, start the program with the environment variable `G_MESSAGES_DEBUG=gobject-ref`.

## Translation

We're using [Weblate](https://hosted.weblate.org/engage/video-downloader/) to translate the UI. So feel free, to contribute translations over there.

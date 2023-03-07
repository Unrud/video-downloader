# Video Downloader

[![Translation status](https://hosted.weblate.org/widgets/video-downloader/-/gui/svg-badge.svg)](https://hosted.weblate.org/engage/video-downloader/)

Download videos from websites with an easy-to-use interface.
Provides the following features:

  * Convert videos to MP3
  * Supports password-protected and private videos
  * Download single videos or whole playlists
  * Automatically selects a video format based on your quality demands

Based on [yt-dlp](https://github.com/yt-dlp/yt-dlp).

## Installation

<a href='https://flathub.org/apps/details/com.github.unrud.VideoDownloader'><img width='240' alt='Download on Flathub' src='https://flathub.org/assets/badges/flathub-badge-en.png'/></a>

### Alternative installation methods

  * [Snap Store](https://snapcraft.io/video-downloader)
  * [Fedora](https://src.fedoraproject.org/rpms/video-downloader): `sudo dnf install video-downloader`
  * [Arch User Repository](https://aur.archlinux.org/packages/video-downloader)

## Translation

We're using [Weblate](https://hosted.weblate.org/engage/video-downloader/) to translate the UI. So feel free, to contribute translations over there.

## Screenshots

![screenshot 1](https://raw.githubusercontent.com/Unrud/video-downloader/master/screenshots/1.png)

![screenshot 2](https://raw.githubusercontent.com/Unrud/video-downloader/master/screenshots/2.png)

![screenshot 3](https://raw.githubusercontent.com/Unrud/video-downloader/master/screenshots/3.png)

## Hidden configuration options

The behavior of the program can be tweaked with GSettings.

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

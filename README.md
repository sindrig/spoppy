# spoppy
Lightweight Spotify Command-Line interface for Linux
[![Build Status](https://travis-ci.org/sindrig/spoppy.svg?branch=master)](https://travis-ci.org/sindrig/spoppy)

## Requirements

Python 2.7 or Python 3.3+

See requirements.txt for required python packages. They will be automatically installed when you install via pip.

You will need a Spotify Premium account and a Spotify username (if you signed up via Facebook you can [follow the instructions here](https://community.spotify.com/t5/Help-Accounts-and-Subscriptions/How-do-i-find-my-username-when-using-Facebook-login/td-p/859795) to get your username).

You will need libspotify, pyaudio or pyalsaaudio, and libffi-dev installed.

You will either need to install `pyaudio` or `alsaaudio` by (pyaudio instructions [Here](https://people.csail.mit.edu/hubert/pyaudio/) and pyalsaaudio instructions [here](http://larsimmisch.github.io/pyalsaaudio/pyalsaaudio.html#installation)).

Use your distribution's package manager for libffi-dev (f.x. `apt-get install libffi-dev`).

To install libspotify, see [Pyspotify installation](https://pyspotify.mopidy.com/en/latest/installation/#install-from-source). (It's also available in the [AUR](https://aur.archlinux.org/packages/libspotify/)).

For DBus integration you'll need python-dbus and python-gobject2. Use your distribution's package manager. Spoppy will work without these packages but won't expose it's DBus procedures.

## Installation

`pip install spoppy`

To install globally you will probably need superuser privileges.

After installation run `spoppy` in your terminal and you're all set!

## Screenshots

### Top menu
![Top menu](/screenshots/top_menu.png?raw=true "Top menu")
### Playlist overview
![Playlist overview](/screenshots/playlist_overview.png?raw=true "Playlist overview")
### Playlist
![Playlist](/screenshots/playlist.png?raw=true "Playlist")
### Player view
![Player](/screenshots/player.png?raw=true "Player")
### Player operations
![Player operations](/screenshots/player_operations.png?raw=true "Player operations")
### Search results
![Search results](/screenshots/search_results.png?raw=true "Search results")
### Certain artists can be banned
![Banned artists](/screenshots/banned_artist.png?raw=true "Banned artists")
### Operations on a specific song
![Song info](/screenshots/song_info.png?raw=true "Song info")

## Development

1. Create a virtualenv (python 2.7 or python 3.3+)
2. Clone this project
3. Activate your virtualenv
4. Install requirements (`pip install -r requirements.txt`)
5. Run `python scripts/spoppy` (you will be asked for username/password)

## DBus integration

1. Run `make install_dbus`
2. Make sure you have python-gobject2 installed
3. Symlink gi (and possibly glib) to your virtualenv (that is, if you're not installing globally!)
4. The service will be available at "/com/spoppy" (f.x. `qdbus com.spoppy /com/spoppy com.spoppy.PlayPause`)

## Debugging

To enable verbose logging, set the `SPOPPY_LOG_LEVEL` environment variable to `'DEBUG'`.

## Testing

`make test`

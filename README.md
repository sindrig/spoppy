# spoppy
Spotify CLI

# Requirements

See requirements.txt
You will need libspotify, libffi-dev and libasound2-dev installed. Use your distribution's package manager.
You will need a Spotify Premium account.

# Development

1. Create python3.4+ virtualenv
2. Acquire a spotify application key from https://devaccount.spotify.com/my-account/keys/
  * Download the Binary key file
3. (optional) Create an ENV file containing these values:
  * export SPOPPY_USERNAME=your-username
  * export SPOPPY_PASSWORD=hunter2
4. Clone this project
5. Activate your virtualenv
6. (if you did #3) Source your ENV file
7. Install requirements
  * pip install -r requirements.txt
8. Run `python spoppy.py` (if you did not create an ENV file you can run `python spoppy.py USERNAME PASSWORD`)

# DBus integration

1. Run `make install_dbus`
2. Make sure you have python-gobject2 installed
3. Symlink gobject (and possibly glib) to your virtualenv
  * ln -s /usr/lib/python3.5/site-packages/gobject/ $VIRTUAL_ENV/lib/python3.5/site-packages/gobject
  * ln -s /usr/lib/python3.5/site-packages/glib/ $VIRTUAL_ENV/lib/python3.5/site-packages/glib
4. The service will be available at "/com/spoppy" (f.x. `qdbus com.spoppy /com/spoppy com.spoppy.PlayPause`)

# Testing

1. Run `pip install nose`
2. Run `make test` from the projects home path

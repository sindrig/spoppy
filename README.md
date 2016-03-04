# spoppy
Spotify CLI

# Requirements

See requirements.txt

You will need libspotify, libffi-dev and libasound2-dev installed. Use your distribution's package manager.

You will need a Spotify Premium account.

# Development

1. Create python3.4+ virtualenv
2. (optional) Create an ENV file containing these values:
  * export SPOPPY_USERNAME=your-username
  * export SPOPPY_PASSWORD=hunter2
3. Clone this project
4. Activate your virtualenv
5. (if you did #2) Source your ENV file
6. Install requirements
  * pip install -r requirements.txt
7. Run `python spoppy.py` (if you did not create an ENV file you can run `python spoppy.py USERNAME PASSWORD`)

# DBus integration

1. Run `make install_dbus`
2. Make sure you have python-gobject2 installed
3. Symlink gobject (and possibly glib) to your virtualenv
  * ln -s /usr/lib/python3.5/site-packages/gobject/ $VIRTUAL_ENV/lib/python3.5/site-packages/gobject
  * ln -s /usr/lib/python3.5/site-packages/glib/ $VIRTUAL_ENV/lib/python3.5/site-packages/glib
4. The service will be available at "/com/spoppy" (f.x. `qdbus com.spoppy /com/spoppy com.spoppy.PlayPause`)

# Testing

1. Run `pip install nose coverage`
2. Run `make test` from the projects home path

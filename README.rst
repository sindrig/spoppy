spoppy
========
Lightweight Spotify Command-Line interface for Linux

Requirements
==============

See requirements.txt for required python packages.

You will need a Spotify Premium account.

You will need libspotify, libffi-dev and libasound2-dev installed. Use your distribution's package manager.

For DBust integration you'll need python-dbus and python-gobject2. Use your distribution's package manager. Spoppy will work without these packages but won't expose it's DBus procedures.

Installation
==============

:code:`pip install spoppy`

To install globally you will probably need superuser privileges.

After installation run :code:`spoppy` in your terminal and you're all set!

Development
=============

NOTE: This is kind of broken at the moment, see issue #60

#. Create python3.4+ virtualenv
#. (optional) Create an ENV file containing these values:

  * export SPOPPY_USERNAME=your-username
  * export SPOPPY_PASSWORD=hunter2

#. Clone this project
#. Activate your virtualenv
#. (if you did #2) Source your ENV file
#. Install requirements

  * pip install -r requirements.txt

#. Run :code:`python spoppy.py` (if you did not create an ENV file you can run :code:`python spoppy.py USERNAME PASSWORD`)

DBus integration
==================

#. Run `make install_dbus`
#. Make sure you have python-gobject2 installed
#. Symlink gobject (and possibly glib) to your virtualenv

  * ln -s /usr/lib/python3.5/site-packages/gobject/ $VIRTUAL_ENV/lib/python3.5/site-packages/gobject
  * ln -s /usr/lib/python3.5/site-packages/glib/ $VIRTUAL_ENV/lib/python3.5/site-packages/glib

#. The service will be available at "/com/spoppy" (f.x. :code:`qdbus com.spoppy /com/spoppy com.spoppy.PlayPause`)

Testing
=========

:code:`python setup.py test`
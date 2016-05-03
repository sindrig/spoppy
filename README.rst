spoppy
========
Lightweight Spotify Command-Line interface for Linux

Requirements
==============

Python 2.7 or Python 3.3+

See requirements.txt for required python packages. They will be automatically installed when you install via pip.

You will need a Spotify Premium account and a Spotify username (if you signed up via Facebook you can `follow the instructions here <https://community.spotify.com/t5/Help-Accounts-and-Subscriptions/How-do-i-find-my-username-when-using-Facebook-login/td-p/859795>`_ to get your username).

You will need libspotify, libffi-dev and libasound2-dev installed.

Use your distribution's package manager for libffi-dev and libasound2-dev (f.x. :code:`apt-get install libffi-dev libasound2-dev`).

To install libspotify, see `Pyspotify installation <https://pyspotify.mopidy.com/en/latest/installation/#install-from-source>`_. (It's also available in the `AUR <https://aur.archlinux.org/packages/libspotify/>`_).

For DBus integration you'll need python-dbus and python-gobject2. Use your distribution's package manager. Spoppy will work without these packages but won't expose it's DBus procedures.

Installation
==============

:code:`pip install spoppy`

To install globally you will probably need superuser privileges.

After installation run :code:`spoppy` in your terminal and you're all set!

Development
=============

1. Create a virtualenv (python 2.7 or python 3.3+)
2. Clone this project
3. Activate your virtualenv
4. Install requirements (:code:`pip install -r requirements.txt`)
5. Run :code:`python scripts/spoppy` (you will be asked for username/password)

DBus integration
==================

1. Run `make install_dbus`
2. Make sure you have python-gobject2 installed
3. Symlink gi (and possibly glib) to your virtualenv (that is, if you're not installing globally!)
4. The service will be available at "/com/spoppy" (f.x. :code:`qdbus com.spoppy /com/spoppy com.spoppy.PlayPause`)

Testing
=========

:code:`make test`
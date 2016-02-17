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
3. Create an ENV file containing these values:
  * export SPOPPY_USERNAME=your-username
  * export SPOPPY_PASSWORD=hunter2
  * export SPOPPY_LIBSPOTIFY_APP_KEY=/path/to/spotify_appkey.key
4. Clone this project
5. Activate your virtualenv
6. Source your ENV file
7. Install requirements
  * pip install -r requirements.txt
8. Run `python spoppy.py`

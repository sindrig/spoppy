if [ -z "${VIRTUAL_ENV-}" ] ; then
    echo "\$VIRTUAL_ENV not set, aborting"
    exit 1
fi
mkdir -p .tmp
cd .tmp
wget https://dbus.freedesktop.org/releases/dbus-python/dbus-python-1.2.0.tar.gz
tar zxvf dbus-python-1.2.0.tar.gz
cd dbus-python-1.2.0
./configure --prefix=$VIRTUAL_ENV
make
make install

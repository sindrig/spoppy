
install_dbus: clean
	./install_dbus.sh

clean:
	rm -rf .tmp

test:
	nosetests -s --with-coverage --cover-package=spoppy

upload:
	python setup.py sdist upload -r pypi

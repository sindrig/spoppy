
install_dbus: clean
	./install_dbus.sh

clean:
	rm -rf .tmp .eggs build dist *.egg-info

test: clean
	# nosetests -s --with-coverage --cover-package=spoppy
	python setup.py test

upload:
	python setup.py sdist upload -r pypi

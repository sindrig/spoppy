
install_dbus: clean
	./install_dbus.sh

clean:
	rm -rf .tmp .eggs build dist *.egg-info htmlcov

test: clean
	python setup.py test

coverage: clean
	nosetests -s --with-coverage --cover-package=spoppy --cover-html --cover-html-dir=htmlcov

upload:
	python setup.py sdist upload -r pypi

test_upload:
	python setup.py sdist upload -r pypitest

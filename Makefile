.ONESHELL:
init:
	python -m venv ${HOME}/virtualenv/scrapy-athlinks
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	pip install --editable .[lint,dev]

test:
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	python -m unittest tests/*.py

clean:
	rm -Rf *.egg-info build dist

testpublish:
	$(MAKE) clean
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	python -m build .
	twine check dist/*
	twine upload -r testpypi dist/*

publish:
	$(MAKE) clean
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	python -m build .
	twine check dist/*
	twine upload dist/*

.ONESHELL:
SHELL = /usr/bin/bash
init:
	python -m venv ${HOME}/virtualenv/scrapy-athlinks
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	pip install --editable .[lint,dev]

test:
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	python -m unittest tests/*.py

testpublish:
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	python -m build .
	twine check dist/*
	twine upload -r testpypi dist/*

publish:
	. ${HOME}/virtualenv/scrapy-athlinks/bin/activate
	python -m build .
	twine check dist/*
	twine upload dist/*

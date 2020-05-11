.PHONY: tests all unit functional clean dependencies tdd docs html purge dist
# Config
OSNAME			:= $(shell uname)

DEBIAN_FRONTEND		:= noninteractive
PYTHONUNBUFFERED	:= true

ifeq ($(OSNAME), Linux)
OPEN_COMMAND		:= gnome-open
OSDEPS			:= sudo apt-get update && sudo apt-get -y install libssl-dev python-dev libgnutls28-dev libtool  build-essential file libmysqlclient-dev libffi-dev libev-dev libevent-dev libxml2-dev libxslt1-dev libnacl-dev redis-tools vim htop aptitude lxc-docker-1.9.1 figlet supervisor virtualenvwrapper
else
OPEN_COMMAND		:= open
OSDEPS			:= brew install redis libevent libev
endif




TZ				:= UTC
PYTHONPATH			:= $(shell pwd)
AGENTZERO_CONFIG_PATH		:= $(shell pwd)/tests/agentzero.cfg
AGENTZERO_LOGLEVEL		:= DEBUG
AGENTZERO_API_ADDRESS		:=
AGENTZERO_PUBLISHER_ADDRESS	:=
PATH				:= $(PATH):$(shell pwd)
executable			:= poetry run python -m agentzero.console.main
export TZ
export PATH
export PYTHONPATH
export AGENTZERO_LOGLEVEL
export AGENTZERO_CONFIG_PATH
export DEBIAN_FRONTEND
export PYTHONUNBUFFERED
export AGENTZERO_API_ADDRESS
export AGENTZERO_PUBLISHER_ADDRESS

GIT_ROOT		:= $(shell dirname $(realpath $(firstword $(MAKEFILE_LIST))))
DOCS_ROOT		:= $(GIT_ROOT)/docs
HTML_ROOT		:= $(DOCS_ROOT)/build/html
VENV_ROOT		:= $(GIT_ROOT)/.venv
VENV			?= $(VENV_ROOT)
BENTO_BIN		:= $(shell which bento)
DOCS_INDEX		:= $(HTML_ROOT)/index.html
BENTO_EMAIL		:= gabriel@nacaolivre.org

export VENV

all: dependencies tests docs

$(VENV):  # creates $(VENV) folder if does not exist
	python3 -mvenv $(VENV)
	$(VENV)/bin/pip install -U pip setuptools wheel

$(VENV)/bin/sphinx-build $(VENV)/bin/twine $(VENV)/bin/nosetests $(VENV)/bin/python $(VENV)/bin/pip: # installs latest pip
	test -e $(VENV)/bin/pip || make $(VENV)
	$(VENV)/bin/pip install -r development.txt
	$(VENV)/bin/pip install -e .

# Runs the unit and functional tests
tests: $(VENV)/bin/nosetests  # runs all tests
	$(VENV)/bin/nosetests tests --with-random --cover-erase

tdd: $(VENV)/bin/nosetests  # runs all tests
	$(VENV)/bin/nosetests tests --with-watch --cover-erase

# Install dependencies
dependencies: | $(VENV)/bin/nosetests
	$(VENV)/bin/pip install -r development.txt

# runs unit tests
unit: $(VENV)/bin/nosetests  # runs only unit tests
	$(VENV)/bin/nosetests --cover-erase tests/unit

# runs functional tests
functional: $(VENV)/bin/nosetests  # runs functional tests
	$(VENV)/bin/nosetests tests/functional


$(DOCS_INDEX): | $(VENV)/bin/sphinx-build
	cd docs && make html

html: $(DOCS_INDEX)

docs: $(DOCS_INDEX)
	open $(DOCS_INDEX)

release: | clean bento unit functional tests html
	@rm -rf dist/*
	@./.release
	@make pypi

bento: | $(BENTO_BIN)
	$(BENTO_BIN) --agree --email=$(BENTO_EMAIL) check --all

dist: clean | $(VENV)/bin/python
	$(VENV)/bin/python setup.py build sdist

pypi: dist | $(VENV)/bin/twine
	$(VENV)/bin/twine check dist/*.tar.gz
	# $(VENV)/bin/twine upload dist/*.tar.gz

# cleanup temp files
clean:
	rm -rf $(HTML_ROOT) build dist


# purge all virtualenv and temp files, causes everything to be rebuilt
# from scratch by other tasks
purge: clean
	rm -rf $(VENV)



os-dependencies:
	$(OSDEPS)

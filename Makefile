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

all: tests docs

TZ				:= UTC
PYTHONPATH			:= $(shell pwd)
AGENTZERO_CONFIG_PATH		:= $(shell pwd)/tests/agentzero.cfg
AGENTZERO_LOGLEVEL		:= DEBUG
AGENTZERO_API_ADDRESS		:=
AGENTZERO_PUBLISHER_ADDRESS	:=
PATH				:= $(PATH):$(shell pwd)
executable			:= python -m agentzero.console.main
export TZ
export PATH
export PYTHONPATH
export AGENTZERO_LOGLEVEL
export AGENTZERO_CONFIG_PATH
export DEBIAN_FRONTEND
export PYTHONUNBUFFERED
export AGENTZERO_API_ADDRESS
export AGENTZERO_PUBLISHER_ADDRESS

tests: lint unit functional

setup: os-dependencies ensure-dependencies

os-dependencies:
	$(OSDEPS)

lint:
	@printf "\033[1;33mChecking for static errors\033[0m\n"
	@find agentzero -name '*.py' | grep -v node | xargs flake8 --ignore=E501

clean:
	git clean -Xdf

unit:
	nosetests -x --with-randomly --with-coverage --cover-erase --cover-package=agentzero --verbosity=2 -s --rednose tests/unit

functional:
	nosetests -x  --with-randomly --with-coverage --cover-erase \
	    --cover-package=agentzero.core \
	    --cover-package=agentzero.serializers \
	    --verbosity=2 -s --rednose tests/functional



tests: functional

prepare: remove
	ensure-dependencies

remove:
	-@pip uninstall -y agentzero

ensure-dependencies:
	@CFLAGS='-std=c99' pip install -r development.txt

release: tests
	@./.release
	@python setup.py sdist register upload

list:
	@$(executable) list

.PHONY: html-docs docs

html-docs:
	cd docs && make html

docs: html-docs
	$(OPEN_COMMAND) docs/build/html/index.html

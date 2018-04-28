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
executable			:= pipenv run python -m agentzero.console.main
PIPENV_IGNORE_VIRTUALENVS	:= 1
export TZ
export PATH
export PYTHONPATH
export AGENTZERO_LOGLEVEL
export AGENTZERO_CONFIG_PATH
export DEBIAN_FRONTEND
export PYTHONUNBUFFERED
export AGENTZERO_API_ADDRESS
export AGENTZERO_PUBLISHER_ADDRESS
export PIPENV_IGNORE_VIRTUALENVS

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
	@pipenv run nosetests --cover-erase --cover-package=agentzero \
	    tests/unit


functional:
	@pipenv run nosetests \
	    --cover-package=agentzero.core \
	    --cover-package=agentzero.serializers \
	    tests/functional



tests: functional

prepare: remove
	ensure-dependencies

remove:
	-@pipenv uninstall -y agentzero

ensure-dependencies:
	@CFLAGS='-std=c99' pipenv install --dev --skip-lock -r development.txt

release: tests
	@./.release
	@rm -rf dist
	@pipenv run python setup.py sdist
	@pipenv run twine upload dist/*.tar.gz

list:
	@$(executable) list

.PHONY: html-docs docs

html-docs:
	cd docs && make html

docs: html-docs
	$(OPEN_COMMAND) docs/build/html/index.html

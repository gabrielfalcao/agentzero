FROM ubuntu:trusty

ENV DEBIAN_FRONTEND  noninteractive
ENV PYTHONUNBUFFERED true
ENV VIRTUAL_ENV      /srv/venv
ENV PATH             $VIRTUAL_ENV/bin:$PATH

MAINTAINER gabriel@canary.is

RUN apt-get update \
  && apt-get --yes --no-install-recommends install \
    gcc \
    g++ \
    libc6-dev \
    python2.7 \
    python2.7-dev \
    python-pip \
    libssl-dev \
    libgnutls28-dev \
    libtool \
    build-essential \
    bash-completion \
    file \
    libmysqlclient-dev \
    libffi-dev \
    libev-dev \
    libevent-dev \
    libxml2-dev \
    libxslt1-dev \
    libnacl-dev \
    redis-tools \
    vim \
    htop \
    aptitude \
  && rm -rf /var/lib/apt/lists/*

RUN pip install virtualenv \
  && mkdir -p "${VIRTUAL_ENV}" \
  && virtualenv "${VIRTUAL_ENV}"

RUN adduser --quiet --system --uid 1000 --group --disabled-login \
  --home /srv/agentzero agentzero

WORKDIR /srv/agentzero
RUN mkdir -p /srv/agentzero

ENV VVERSION 1
COPY *.txt /tmp/
RUN pip install -U pip

# RUN pip install -r /tmp/requirements.txt
RUN pip install -r /tmp/development.txt

COPY . /srv/agentzero/

ENV PATH /srv/agentzero/bin
ENV PYTHONPATH /srv/agentzero/

#RUN python setup.py install

#USER agentzero

CMD ["agentzero"]

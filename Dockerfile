FROM python:3.7.6-slim-buster

ENV PYTHONPATH /sources

RUN apt-get update && \
    apt-get upgrade -y && \
    apt-get install -y php7.3 perl cpanminus make gcc curl git && \
    cpanm Clone Algorithm::Combinatorics

WORKDIR /sources
ADD ./requirements.txt /sources/requirements.txt
RUN pip install -r /sources/requirements.txt

ADD . /sources

RUN ["chmod", "+x", "/sources/run_server.sh"]
RUN ["chmod", "+x", "/sources/run_tasks.sh"]

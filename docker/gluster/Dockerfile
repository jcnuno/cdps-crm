FROM ubuntu:17.04

RUN apt-get update
RUN apt-get install -y glusterfs-server

RUN mkdir /nas

EXPOSE 111 24007 24008 2049 38465 38466 38467 49152 49153 49514

CMD service glusterfs-server restart && tail -f /dev/null

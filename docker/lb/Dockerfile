FROM ubuntu:17.04

RUN apt-get update
RUN apt-get install -y build-essential wget

RUN wget --no-check-certificate https://crossroads.e-tunity.com/downloads/versions/crossroads-2.81.tar.gz
RUN tar -xvf crossroads-2.81.tar.gz
WORKDIR crossroads-2.81

RUN make install 

EXPOSE 8001
EXPOSE 80

CMD xr --server tcp:0:80 -dr --backend s1:3000 --backend s2:3000 --backend s3:3000 --web-interface 0:8001 
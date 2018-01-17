FROM ubuntu:17.04

RUN apt-get update
RUN apt-get install -y build-essential wget ufw

RUN wget --no-check-certificate https://crossroads.e-tunity.com/downloads/versions/crossroads-2.81.tar.gz
RUN tar -xvf crossroads-2.81.tar.gz
WORKDIR crossroads-2.81

RUN make install 

# Configure local firewall
RUN sed -i "s/IPV6=yes/IPV6=no/" /etc/default/ufw

EXPOSE 8001
EXPOSE 80

CMD bash -c "ufw enable && ufw allow 80/tcp && ufw allow 8001/tcp; \
			 xr --server tcp:0:80 -dr --backend s1:3000 --backend s2:3000 --backend s3:3000 --web-interface 0:8001"
FROM ubuntu:16.04

RUN apt-get update
RUN apt-get install -y build-essential wget ufw libgd2-xpm-dev openssl libssl-dev unzip curl

WORKDIR /root/
RUN wget --no-check-certificate https://crossroads.e-tunity.com/downloads/versions/crossroads-2.81.tar.gz
RUN tar -xvf crossroads-2.81.tar.gz

WORKDIR crossroads-2.81
RUN make install 

# Install NRPE

RUN useradd nagios
WORKDIR /root/
RUN curl -L -O http://nagios-plugins.org/download/nagios-plugins-2.2.1.tar.gz

RUN tar zxf nagios-plugins-2.2.1.tar.gz
WORKDIR nagios-plugins-2.2.1

RUN ./configure --with-nagios-user=nagios --with-nagios-group=nagios --with-openssl

RUN make
RUN make install

WORKDIR /root/
RUN curl -L -O https://github.com/NagiosEnterprises/nrpe/releases/download/nrpe-3.2.1/nrpe-3.2.1.tar.gz
RUN tar zxf nrpe-3.2.1.tar.gz
WORKDIR nrpe-3.2.1

RUN ./configure --enable-command-args --with-nagios-user=nagios --with-nagios-group=nagios --with-ssl=/usr/bin/openssl --with-ssl-lib=/usr/lib/x86_64-linux-gnu --with-init-type=systemd --with-inetd-type=systemd

RUN make all && make install && make install-config && make install-init

RUN sed -i "s+allowed_hosts=127.0.0.1,::1+#allowed_hosts=127.0.0.1,::1+" /usr/local/nagios/etc/nrpe.cfg
RUN sed -i "s+-r -w .15,.10,.05 -c .30,.25,.20+-r -w .85,.75,.65 -c .95,.85,.75+" /usr/local/nagios/etc/nrpe.cfg

# Configure local firewall
RUN sed -i "s/IPV6=yes/IPV6=no/" /etc/default/ufw

EXPOSE 8001
EXPOSE 80
EXPOSE 5666

WORKDIR /root/

CMD bash -c "/usr/local/nagios/bin/nrpe -c /usr/local/nagios/etc/nrpe.cfg -d; \
			 ufw enable && ufw allow 80/tcp && ufw allow 8001/tcp && ufw allow 5666/tcp; \
			 xr --server tcp:0:80 -dr --backend s1:3000 --backend s2:3000 --backend s3:3000 --web-interface 0:8001"
FROM ubuntu:16.04

RUN apt-key adv --keyserver hkp://p80.pool.sks-keyservers.net:80 --recv-keys B97B0AFCAA1A47F044F244A07FCC7D46ACCC4CF8

RUN echo "deb http://apt.postgresql.org/pub/repos/apt/ xenial-pgdg main" > /etc/apt/sources.list.d/pgdg.list

RUN apt-get update 
RUN apt-get install -y python-software-properties software-properties-common postgresql-9.6 postgresql-client-9.6 postgresql-contrib-9.6 build-essential libgd2-xpm-dev openssl libssl-dev unzip curl sudo

RUN	service postgresql start &&\
	sudo -u postgres psql --command "CREATE USER crm with password 'xxxx';" &&\
	sudo -u postgres psql --command "CREATE DATABASE crm;" &&\
	sudo -u postgres psql --command "GRANT ALL PRIVILEGES ON DATABASE crm to crm;" 

RUN echo "host all  all	0.0.0.0/0  md5" >> /etc/postgresql/9.6/main/pg_hba.conf
RUN echo "listen_addresses='*'" >> /etc/postgresql/9.6/main/postgresql.conf

EXPOSE 5432

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

EXPOSE 5666

WORKDIR /root/

# Add VOLUMEs to allow backup of databases
VOLUME  ["/var/lib/postgresql"]

# Set the default command to run when starting the container
CMD /usr/local/nagios/bin/nrpe -c /usr/local/nagios/etc/nrpe.cfg -d && service postgresql restart && tail -f /dev/null
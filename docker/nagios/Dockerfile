FROM ubuntu:17.10

RUN useradd nagios && groupadd nagcmd
RUN usermod -a -G nagcmd nagios

# Install Nagios

RUN apt-get update
RUN apt-get install -y ufw build-essential libgd2-xpm-dev openssl libssl-dev unzip curl apache2 php libapache2-mod-php php-mcrypt php-mysql php-cli nagios-plugins

RUN service apache2 start

WORKDIR /root/
RUN curl -L -O https://assets.nagios.com/downloads/nagioscore/releases/nagios-4.3.4.tar.gz
RUN tar zxf nagios-4.3.4.tar.gz

WORKDIR nagios-4.3.4
RUN ./configure --with-nagios-group=nagios --with-command-group=nagcmd

RUN make all
RUN make install
RUN make install-commandmode
RUN make install-init
RUN make install-config

RUN /usr/bin/install -c -m 644 sample-config/httpd.conf /etc/apache2/sites-available/nagios.conf
RUN usermod -G nagcmd www-data

# Install NRPE

WORKDIR /root/
RUN curl -L -O https://github.com/NagiosEnterprises/nrpe/releases/download/nrpe-3.2.1/nrpe-3.2.1.tar.gz
RUN tar zxf nrpe-3.2.1.tar.gz

WORKDIR nrpe-3.2.1

RUN ./configure
RUN make check_nrpe
RUN make install-plugin

# Configure Nagios

WORKDIR /root/
RUN sed -i "s+#cfg_dir=/usr/local/nagios/etc/servers+cfg_dir=/usr/local/nagios/etc/servers+" /usr/local/nagios/etc/nagios.cfg

RUN mkdir -p /usr/local/nagios/etc/servers/

COPY config/servers/ /usr/local/nagios/etc/servers/
COPY config/commands.cfg /usr/local/nagios/etc/objects/commands.cfg
COPY config/localhost.cfg /usr/local/nagios/etc/objects/localhost.cfg

RUN a2enmod rewrite
RUN a2enmod cgi

RUN htpasswd -b -c /usr/local/nagios/etc/htpasswd.users nagiosadmin xxxx
RUN ln -s /etc/apache2/sites-available/nagios.conf /etc/apache2/sites-enabled/

COPY config/nagios.service /etc/systemd/system/nagios.service

# FIX 'no output on stdout' ERROR
RUN cp /usr/lib/nagios/plugins/check_* /usr/local/nagios/libexec

EXPOSE 80 5666

# Configure local firewall
RUN sed -i "s/IPV6=yes/IPV6=no/" /etc/default/ufw

WORKDIR /root/

CMD bash -c "service nagios start && service apache2 start; \
			 ufw enable && ufw allow 80/tcp && ufw allow 5666/tcp && tail -f /dev/null"

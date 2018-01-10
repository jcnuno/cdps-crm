#!/bin/sh

# INSTALL NAGIOS
	
sudo useradd nagios 
sudo groupadd nagcmd
sudo usermod -a -G nagcmd nagios

cd /root/
tar zxf nagios-$1.tar.gz

cd nagios-$1
./configure --with-nagios-group=nagios --with-command-group=nagcmd

make all
sudo make install
sudo make install-commandmode
sudo make install-init
sudo make install-config

sudo /usr/bin/install -c -m 644 sample-config/httpd.conf /etc/apache2/sites-available/nagios.conf

sudo usermod -G nagcmd www-data


# INSTALL check_rpe PLUGIN

cd /root/

tar zxf nrpe-$2.tar.gz
cd nrpe-$2

./configure
make check_nrpe
sudo make install-plugin


# CONFIGURING NAGIOS

sed -i "s+#cfg_dir=/usr/local/nagios/etc/servers+cfg_dir=/usr/local/nagios/etc/servers+" /usr/local/nagios/etc/nagios.cfg

sudo mkdir /usr/local/nagios/etc/servers
sudo cp /root/default_config/commands.cfg /usr/local/nagios/etc/objects/commands.cfg

sudo a2enmod rewrite
sudo a2enmod cgi

sudo htpasswd -b -c /usr/local/nagios/etc/htpasswd.users nagiosadmin xxxx
sudo ln -s /etc/apache2/sites-available/nagios.conf /etc/apache2/sites-enabled/

sudo systemctl restart apache2
sudo cp /root/default_config/nagios.service /etc/systemd/system/nagios.service

sudo systemctl enable /etc/systemd/system/nagios.service
sudo systemctl start nagios


# FIX 'no output on stdout' ERROR
cp /usr/lib/nagios/plugins/check_* /usr/local/nagios/libexec

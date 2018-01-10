#!/bin/sh

# INSTALL NPRE

sudo useradd nagios
cd /root/
tar zxf nagios-plugins-$1.tar.gz

cd nagios-plugins-$1

./configure --with-nagios-user=nagios --with-nagios-group=nagios --with-openssl
make
sudo make install

sleep 3

tar zxf nrpe-$2.tar.gz
cd nrpe-$2

./configure --enable-command-args --with-nagios-user=nagios --with-nagios-group=nagios --with-ssl=/usr/bin/openssl --with-ssl-lib=/usr/lib/x86_64-linux-gnu

make all
sudo make install
sudo make install-config
sudo make install-init

sed -i "s+allowed_hosts=127.0.0.1,::1+allowed_hosts=127.0.0.1,::1,your_nagios_server_private_ip+" /usr/local/nagios/etc/nrpe.cfg

sudo systemctl start nrpe.service


# FIX 'no output on stdout' ERROR
cp /usr/lib/nagios/plugins/check_* /usr/local/nagios/libexec

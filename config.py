#! /usr/bin/python

'''
Despliegue de un sistema CRM escalable
======================================

Script de configuracion automatica para una implementacion de la 
arquitectura completa de un sistema CRM escalable y fiable basado
en el proyecto CRM utilizado en otras asignaturas. Se utilizaran los 
elementos tipicos de las arquitecturas actuales: firewall, balanceador 
de carga, servidores front-end corriendo la aplicacion, bases de datos 
y servidores de almacenamiento.
'''

import argparse
import logging
import os
import sys
import json
from subprocess import call, check_output
from contextlib import contextmanager
from time import time, sleep

logging.basicConfig(level=logging.INFO, format='%(levelname)s:%(name)s: %(message)s')
logger = logging.getLogger('CDPS')

N_SERVERS_DEFAULT = 3
N_SERVERS_CLUSTER_DEFAULT = 3

POSTGRES_URL = 'postgres://crm:xxxx@10.1.4.31:5432/crm'

NAGIOS_VERSION = '4.3.4'
NAGIOS_PLUGINS_VERSION = '2.2.1'
NRPE_VERSION = '3.2.1'

devnull = open(os.devnull, 'w')

path = os.path.abspath(__file__).split('/')
path.pop()
path = '/'.join(path)

NAGIOS_HOSTS = json.load(open(path + '/nagios.json'))


def main():
	parser = argparse.ArgumentParser(description='Configuracion automatica del despliegue de un sistema CRM escalable')

	parser.add_argument('FILE', help='VNX File para crear el escenario')

	parser.add_argument('-c', '--create', help='crea y arranca el escenario', action='store_true')
	parser.add_argument('-d', '--destroy', help='destruye el escenario y todos los cambios relizados', action='store_true')

	parser.add_argument('--no-console', help='arrancar el escenario sin mostrar las consolas', action='store_false')

	parser.add_argument('--add-server', help='anade un servidor web al escenario', action='store_true')

	args = parser.parse_args()

	if not os.path.exists(args.FILE):
		logger.error('El archivo seleccionado no existe o esta en otro directorio')
		sys.exit()

	with timer('Accion terminada'):
		if args.create:			# Creamos el escenario inicial
			create(args.FILE, args.no_console)
			#bbdd()					# Creamos la base de datos
			gestion()				# Configuramos el servidor de gestion
			#storage()				# Creamos el GlusterFS
			#crm()					# Desplegamos la aplicacion
			load_balancer()			# Configuramos el balancedor
			#firewall()				# Configuramos el cortafuegos
			nagios()				# Configuramos Nagios
		elif args.destroy:		# Destruimos todo el escenario
			destroy(args.FILE)

	print('')


def create(file, console):
	'''
	Creacion del escenario.

	Args:
		file 		VNX File.
		console 	booleano que indica si se muestran las consolas o no.

	'''
	logger.info('Creando escenario...')
	if console:
		call('sudo vnx -f {file} --create'.format(file=file), shell=True, stdout=devnull)
	else:
		call('sudo vnx -f {file} --create --no-console'.format(file=file), shell=True, stdout=devnull)
	logger.info('Escenario creado.')


def destroy(file):
	'''
	Destruccion del escenario completo.

	Args:
		file 		VNX File.

	'''
	logger.info('Destruyendo escenario...')
	call('sudo vnx -f {file} --destroy'.format(file=file), shell=True, stdout=devnull)
	call('ssh-add -d ~/.ssh/ges_rsa', shell=True)
	call('rm ~/.ssh/ges_rsa*', shell=True)
	logger.info('Escenario destruido.')


def firewall():
	'''
	Configuracion del cortafuegos. Se debe permitir unicamente el 
	acceso mediante ping y al puerto 80 de TCP de la direccion 
	balanceador de trafico. 
	Cualquier otro trafico debe de estar prohibido.
	'''
	logger.info('Configurando firewall...')
	call('sudo lxc-attach --clear-env -n fw -- /root/fw.fw', shell=True, stdout=devnull)
	logger.info('Firewall configurado.')


def bbdd():
	'''
	Configuracion de la base de datos PostgreSQL que utilizaran los 
	servidores.
	'''
	logger.info('Configuracion de PostgreSQL')
	name = 'bbdd'
	lxc = 'sudo lxc-attach --clear-env -n {name}'.format(name=name)

	logger.info('\t Configurando la base de datos...')

	cmd_line = [
		'{lxc} -- bash -c "echo \\\"listen_addresses=\'10.1.4.31\'\\\" >> /etc/postgresql/9.6/main/postgresql.conf"'.format(lxc=lxc),
		'{lxc} -- bash -c "echo \\\"host all all 10.1.4.0/24 trust\\\" >> /etc/postgresql/9.6/main/pg_hba.conf"'.format(lxc=lxc),
		'{lxc} -- bash -c "echo \\\"CREATE USER crm with password \'xxxx\';\\\" | sudo -u postgres psql"'.format(lxc=lxc),
		'{lxc} -- bash -c "echo \\\"CREATE DATABASE crm;\\\" | sudo -u postgres psql"'.format(lxc=lxc),
		'{lxc} -- bash -c "echo \\\"GRANT ALL PRIVILEGES ON DATABASE crm to crm;\\\" | sudo -u postgres psql"'.format(lxc=lxc),
		'{lxc} -- bash -c "systemctl restart postgresql"'.format(lxc=lxc)
	]

	for i in range(len(cmd_line)):
		call(cmd_line[i], shell=True)

	logger.info('PostgreSQL configurado.')


def storage():
	'''
	Configuracion del sistema de ficheros GlusterFS que replica la 
	informacion entre los tres servidores nas.
	'''

	logger.info('Configuracion del GlusterFS')

	# Creacion del cluster (desde nas1)
	lxc = 'sudo lxc-attach --clear-env -n {name}'.format(name='nas1')

	cmd_line = 'gluster volume create nas replica {n}'.format(n=N_SERVERS_CLUSTER_DEFAULT)

	for i in range(1, N_SERVERS_CLUSTER_DEFAULT + 1):
		call('{lxc} -- bash -c "gluster peer probe 10.1.4.2{n}"'.format(lxc=lxc, n=str(i)), shell=True, stdout=devnull)

		cmd_line += ' 10.1.4.2{n}:/nas'.format(n=str(i))
		sleep(0.5)

	call('{lxc} -- bash -c "{cmd_line} force"'.format(lxc=lxc, cmd_line=cmd_line), shell=True)
	call('{lxc} -- bash -c "gluster volume start nas"'.format(lxc=lxc), shell=True)

	cmd_line = 'gluster volume set nas network.ping-timeout 5'
	for i in range(1, N_SERVERS_CLUSTER_DEFAULT + 1):
		call('sudo lxc-attach --clear-env -n nas{n} -- bash -c "{cmd_line}"'.format(n=str(i), cmd_line=cmd_line), shell=True, stdout=devnull)

	# Configuracion del cluster desde los servidores web
	for i in range(1, N_SERVERS_DEFAULT + 1):
		lxc = 'sudo lxc-attach --clear-env -n s{n}'.format(n=str(i))
		call('{lxc} -- bash -c "mkdir /mnt/nas"'.format(lxc=lxc), shell=True, stdout=devnull)
		call('{lxc} -- bash -c "mount -t glusterfs 10.1.4.21:/nas /mnt/nas"'.format(lxc=lxc), shell=True)

	logger.info('GlusterFS configurado.')


def crm():
	'''
	Instalacion y configuracion  de la aplicacion CRM en los servidores.

	Disponible en https://github.com/CORE-UPM/CRM_2017
	'''
	logger.info('Instalacion del CRM')

	for i in range(1, N_SERVERS_DEFAULT + 1):
		lxc = 'sudo lxc-attach --clear-env -n s{n} --set-var DATABASE_URL={url}'.format(n=str(i), url=POSTGRES_URL)

		call('{lxc} -- bash -c "cd /root; git clone https://github.com/CORE-UPM/CRM_2017.git"'.format(lxc=lxc), shell=True, stdout=devnull)
		call('{lxc} -- bash -c "cd /root/CRM_2017; npm install; npm install forever"'.format(lxc=lxc), shell=True, stdout=devnull, stderr=devnull)

		# Creamos la base de datos solo en un servidor
		if (i == 1):
			call('{lxc} -- bash -c "cd /root/CRM_2017; npm run-script migrate_local; npm run-script seed_local"'.format(lxc=lxc), shell=True)

		# Redirigimos las imagenes al cluster
		if (i == 1):
			call('{lxc} -- bash -c "mkdir /mnt/nas/uploads"'.format(lxc=lxc), shell=True)
		call('{lxc} -- bash -c "ln -s /mnt/nas/uploads /root/CRM_2017/public/uploads"'.format(lxc=lxc), shell=True)
		
		# Arrancamos la aplicacion
		call('{lxc} -- bash -c "cd /root/CRM_2017; ./node_modules/forever/bin/forever start ./bin/www"'.format(lxc=lxc), shell=True)

		logger.info('\t CRM instalado en s{}.'.format(str(i)))

	logger.info('CRM instalado satisfactoriamente.')


def load_balancer():
	'''
	Configuracion del balanceador de trafico para que utilice el 
	algoritmo round-robin.
	'''
	cmd_line = 'sudo lxc-attach --clear-env -n lb -- xr --server tcp:0:80 -dr'

	for i in range(1, N_SERVERS_DEFAULT + 1):
		cmd_line += ' --backend 10.1.3.1{n}:3000'.format(n=str(i))

	cmd_line += ' --web-interface 0:8001 &'

	call(cmd_line, shell=True, stdout=devnull)


def nagios():
	'''
	Configuracion del servidor nagios que monitoriza el resto de 
	servidores
	'''

	logger.info('Configuracion de Nagios')

	# Install and configure nagios on nagios server
	call('sudo lxc-attach --clear-env -n nagios -- /root/nagios_server.sh {nagios} {nrpe}'.format(nagios=NAGIOS_VERSION, nrpe=NRPE_VERSION), shell=True, stdout=devnull)

	# Install nrpe on hosts
	for i in range(len(NAGIOS_HOSTS)):
		call('sudo lxc-attach --clear-env -n {host} -- /root/nagios_server.sh {nagios_plugins} {nrpe}'.format(host=NAGIOS_HOSTS[i]['name'], nagios_plugins=NAGIOS_PLUGINS_VERSION, nrpe=NRPE_VERSION), shell=True, stdout=devnull)
	
	logger.info('Nagios configurado.')


def gestion():
	'''
	Configuracion del servidor de gestion. No se permite conectarse
	por ssh con contrasena, solo con clave rsa.
	'''
	call('ssh-keygen -t rsa -N "" -f "/home/$USER/.ssh/ges_rsa"', shell=True, stdout=devnull)
	logger.info('Se han generado un nuevo par de claves para conectarse al servidor de gestion.')
	logger.info('Las puedes encontrar en ~/.ssh/ges_rsa.')

	key = check_output('cat /home/$USER/.ssh/ges_rsa.pub', shell=True)

	lxc = 'sudo lxc-attach --clear-env -n ges'
	call('{lxc} -- bash -c "echo \'{key}\' >> /root/.ssh/authorized_keys"'.format(lxc=lxc, key=key), shell=True)
	call('{lxc} -- sed -i "s/#PasswordAuthentication yes/PasswordAuthentication no/" /etc/ssh/sshd_config'.format(lxc=lxc), shell=True)
	call('{lxc} -- service ssh restart'.format(lxc=lxc), shell=True)

	call('ssh-add ~/.ssh/ges_rsa', shell=True)


@contextmanager
def timer(name='task', function=logger.info):
    start = time()
    yield start
    end = time()
    function('{} en {} segundos'.format(name, end - start))


if __name__ == '__main__':
	main()
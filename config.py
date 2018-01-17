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
import cPickle as pickle
from subprocess import call, check_output
from contextlib import contextmanager
from xml.etree import ElementTree
from time import time, sleep
from threading import Thread

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
    '''
    Funcion principal del script de configuracion.
    '''

    parser = argparse.ArgumentParser(description='Configuracion automatica del despliegue de un sistema CRM escalable')

    parser.add_argument('FILE', help='VNX File para crear el escenario')

    parser.add_argument('-c', '--create', help='crea y arranca el escenario', action='store_true')
    parser.add_argument('-d', '--destroy', help='destruye el escenario y todos los cambios relizados', action='store_true')

    parser.add_argument('--no-console', help='arrancar el escenario sin mostrar las consolas', action='store_false')

    parser.add_argument('--add-server', help='anade un servidor web al escenario', action='store_true')
    parser.add_argument('--remove-server', help='elimina un servidor web del escenario', action='store_true')

    args = parser.parse_args()

    if not os.path.exists(args.FILE):
        logger.error('El archivo seleccionado no existe o esta en otro directorio')
        sys.exit()

    with timer('Accion terminada'):
        if args.create:         # Creamos el escenario inicial
            create(args.FILE, args.no_console)
            bbdd()                  # Creamos la base de datos
            gestion()               # Configuramos el servidor de gestion
            storage()               # Creamos el GlusterFS
            crm()                   # Desplegamos la aplicacion
            load_balancer()         # Configuramos el balancedor
            firewall()              # Configuramos el cortafuegos
            nagios()                # Configuramos Nagios
        elif args.destroy:      # Destruimos todo el escenario
            destroy(args.FILE)
        elif args.add_server:   # Anadimos un nuevo servidor
            tree = ElementTree.parse(args.FILE)
            if len(tree.findall('vm')) > 1:
                logger.error('Los servidores tienen que ser anadidos de uno en uno.')
                sys.exit()
            add_server(
                tree.find('vm').attrib['name'],
                tree.find('vm/if[@net="LAN3"]/ipv4').text.split('/')[0],
                tree.find('vm/if[@net="LAN5"]/ipv4').text.split('/')[0],
                args.no_console,
                args.FILE
            )
        elif args.remove_server:
            tree = ElementTree.parse(args.FILE)
            if len(tree.findall('vm')) > 1:
                logger.error('Los servidores tienen que ser eliminados de uno en uno.')
                sys.exit()
            remove_server(
                tree.find('vm').attrib['name'],
                args.FILE
            )

    print('')


def create(file, console):
    '''
    Creacion del escenario.

    Args:
        file        VNX File.
        console     booleano que indica si se muestran las consolas o no.

    '''
    logger.info('Creando escenario...')
    if console:
        call('sudo vnx -f {file} --create'.format(file=file), shell=True, stdout=devnull)
    else:
        call('sudo vnx -f {file} --create --no-console'.format(file=file), shell=True, stdout=devnull)

    logger.info('Waiting for Virtual Machines to turn on.')
    print_progress(0, 30, prefix='Progress:', suffix='Complete', bar_length=30)
    for i in range(30):
        sleep(1)
        print_progress(i + 1, 30, prefix='Progress:', suffix='Complete', bar_length=30)
    logger.info('Done.')

    logger.info('Escenario creado.')


def destroy(file):
    '''
    Destruccion del escenario completo.

    Args:
        file        VNX File del escenario principal.

    '''
    logger.info('Destruyendo escenario...')
    call('sudo vnx -f {file} --destroy'.format(file=file), shell=True, stdout=devnull)

    if os.path.exists('./.servers_added'):
        servers = pickle.load(open('./.servers_added', 'rb'))
        for i in range(len(servers)):
            call('sudo vnx -f {file} --destroy'.format(file=servers[i]['file']), shell=True, stdout=devnull)
        call('rm ./.servers_added', shell=True)

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
    call('sudo lxc-attach --clear-env -n nagios -- bash -c "/root/nagios_server.sh {nagios} {nrpe}"'.format(nagios=NAGIOS_VERSION, nrpe=NRPE_VERSION), shell=True, stdout=devnull)

    # Install nrpe on hosts
    threads = []
    for i in range(len(NAGIOS_HOSTS)):
        threads.append(Thread(target=installNRPE, args=(NAGIOS_HOSTS[i]['name'],)))

    for thread in threads:
        thread.daemon = True                        # Daemonize thread
        thread.start()                              # Start the execution

    logger.info('Instalando plugin nrpe en los hosts...')
    print_progress(0, len(threads), prefix='Progress:', suffix='Complete', bar_length=30)
    for thread in threads:
        thread.join()                               # Wait to finish thread
        print_progress(threads.index(thread) + 1, len(threads), prefix='Progress:', suffix='Complete', bar_length=30)
    logger.info('Done.')

    # Connecting hosts to Nagios
    for i in range(len(NAGIOS_HOSTS)):
        cmd_line = [
            'cp /root/default_config/default_remote.cfg /usr/local/nagios/etc/servers/{name}.cfg'.format(name=NAGIOS_HOSTS[i]['name']),
            'sed -i "s/remote_name_machine/{name}/g" /usr/local/nagios/etc/servers/{name}.cfg'.format(name=NAGIOS_HOSTS[i]['name']),
            'sed -i "s/remote_description/{description}/g" /usr/local/nagios/etc/servers/{name}.cfg'.format(name=NAGIOS_HOSTS[i]['name'], description=NAGIOS_HOSTS[i]['description']),
            'sed -i "s/remote_ip_address/{ip}/g" /usr/local/nagios/etc/servers/{name}.cfg'.format(name=NAGIOS_HOSTS[i]['name'], ip=NAGIOS_HOSTS[i]['ip'])
        ]
        for line in range(len(cmd_line)):
            call('sudo lxc-attach --clear-env -n nagios -- {cmd}'.format(cmd=cmd_line[line]), shell=True)

    call('sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart nagios', shell=True)
    
    logger.info('Nagios configurado.')


def installNRPE(name):
    '''
    Instalacion del plugin nrpe en diferentes hosts en background, para instalarlo
    en todos al mismo tiempo y ahorrar tiempo de ejecucion.

    Args:
        name        host donde realizar la instalacion.

    '''
    call('sudo lxc-attach --clear-env -n {host} -- bash -c "/root/nagios_host.sh {nagios_plugins} {nrpe}"'.format(
        host=name, 
        nagios_plugins=NAGIOS_PLUGINS_VERSION, 
        nrpe=NRPE_VERSION
    ), shell=True, stdout=devnull, stderr=devnull)

    cmd_line = [
        'sed -i "s+-r -w .15,.10,.05 -c .30,.25,.20+-r -w .85,.75,.65 -c .95,.85,.75+" /usr/local/nagios/etc/nrpe.cfg',
        'sudo systemctl restart nrpe.service'
    ]
    for line in range(len(cmd_line)):
        call('sudo lxc-attach --clear-env -n {host} -- {cmd}'.format(host=name, cmd=cmd_line[line]), shell=True, stdout=devnull, stderr=devnull)


def gestion():
    '''
    Configuracion del servidor de gestion. No se permite conectarse
    por ssh con contrasena, solo con clave rsa.
    '''
    if not os.path.exists('/home/' + os.environ['USER'] + '/.ssh/ges_rsa'):
        call('ssh-keygen -t rsa -N "" -f "/home/$USER/.ssh/ges_rsa"', shell=True, stdout=devnull)
        logger.info('Se han generado un nuevo par de claves para conectarse al servidor de gestion.')
        logger.info('Las puedes encontrar en ~/.ssh/ges_rsa.')

    key = check_output('cat /home/$USER/.ssh/ges_rsa.pub', shell=True)

    lxc = 'sudo lxc-attach --clear-env -n ges'
    call('{lxc} -- bash -c "echo \'{key}\' >> /root/.ssh/authorized_keys"'.format(lxc=lxc, key=key), shell=True)
    call('{lxc} -- sed -i "s/#PasswordAuthentication yes/PasswordAuthentication no/" /etc/ssh/sshd_config'.format(lxc=lxc), shell=True)
    call('{lxc} -- service ssh restart'.format(lxc=lxc), shell=True)


def add_server(name, lb_ip, nagios_ip, console, file):
    '''
    Anadir un servidor para alojar la aplicacion.
    - Se configura el servidor (aplicacion y gluster).
    - Se arranca de nuevo el balanceador de trafico para anadir el servidor.
    - Se anade Nagios al nuevo servidor.

    Args:
        name        nombre del servidor.
        lb_ip       ip de la interfaz del servidor conectada al lb.
        nagios_ip   ip de la interfaz del servidor conectada a nagios.
        console     booleano que indica si se muestra la consola o no.
        file        VNX File.

    '''

    # Guardamos los datos del nuevo servidor
    if not os.path.exists('./.servers_added'):
        call('touch .servers_added', shell=True)
        pickle.dump([], open('./.servers_added', 'wb'))

    servers = pickle.load(open('./.servers_added', 'rb'))

    for i in range(len(servers)):
        if servers[i]['name'] == name:
            logger.error('Servidor ya disponible en {ip}.'.format(ip=lb_ip))
            sys.exit()

    servers.append({
        'name': name,
        'lb_ip': lb_ip,
        'file': file,
    })
    pickle.dump(servers, open('./.servers_added', 'wb'))

    # Creamos el escenario
    if console:
        call('sudo vnx -f {file} --create'.format(file=file), shell=True, stdout=devnull)
    else:
        call('sudo vnx -f {file} --create --no-console'.format(file=file), shell=True, stdout=devnull)

    logger.info('Waiting for Virtual Machine to turn on.')
    print_progress(0, 30, prefix='Progress:', suffix='Complete', bar_length=30)
    for i in range(30):
        sleep(1)
        print_progress(i + 1, 30, prefix='Progress:', suffix='Complete', bar_length=30)
    logger.info('Done.')

    # Configuramos la aplicacion
    lxc = 'sudo lxc-attach --clear-env -n {name} --set-var DATABASE_URL={url}'.format(name=name, url=POSTGRES_URL)

    call('{lxc} -- bash -c "cd /root/; git clone https://github.com/CORE-UPM/CRM_2017.git"'.format(lxc=lxc), shell=True, stdout=devnull)
    call('{lxc} -- bash -c "cd /root/CRM_2017; npm install; npm install forever"'.format(lxc=lxc), shell=True, stdout=devnull, stderr=devnull)
    
    # Arrancamos la aplicacion
    call('{lxc} -- bash -c "cd /root/CRM_2017; ./node_modules/forever/bin/forever start ./bin/www"'.format(lxc=lxc), shell=True)

    logger.info('CRM instalado en .'.format(name))

    # Montamos el gluster
    call('{lxc} -- bash -c "mkdir /mnt/nas"'.format(lxc=lxc), shell=True, stdout=devnull)
    call('{lxc} -- bash -c "mount -t glusterfs 10.1.4.21:/nas /mnt/nas"'.format(lxc=lxc), shell=True)
    call('{lxc} -- bash -c "ln -s /mnt/nas/uploads /root/CRM_2017/public/uploads"'.format(lxc=lxc), shell=True)

    logger.info('Sistema de archivos compartidos montado.')

    # Arrancamos el balanceador de nuevo
    call('sudo lxc-attach --clear-env -n lb -- killall xr', shell=True)
    cmd_line = 'sudo lxc-attach --clear-env -n lb -- xr --server tcp:0:80 -dr'

    for i in range(1, N_SERVERS_DEFAULT + 1):
        cmd_line += ' --backend 10.1.3.1{n}:3000'.format(n=str(i))

    for i in range(len(servers)):
        cmd_line += ' --backend {ip}:3000'.format(ip=servers[i]['lb_ip'])

    cmd_line += ' --web-interface 0:8001 &'

    call(cmd_line, shell=True, stdout=devnull)

    logger.info('Balanceador actualizado.')

    # Reconfiguramos Nagios para monitorizar el nuevo servidor
    logger.info('Actualizando Nagios...')
    installNRPE(name)

    cmd_line = [
        'cp /root/default_config/default_remote.cfg /usr/local/nagios/etc/servers/{name}.cfg'.format(name=name),
        'sed -i "s/remote_name_machine/{name}/g" /usr/local/nagios/etc/servers/{name}.cfg'.format(name=name),
        'sed -i "s/remote_description/Servidor {description}/g" /usr/local/nagios/etc/servers/{name}.cfg'.format(name=name, description=name),
        'sed -i "s/remote_ip_address/{ip}/g" /usr/local/nagios/etc/servers/{name}.cfg'.format(name=name, ip=nagios_ip)
    ]
    for line in range(len(cmd_line)):
        call('sudo lxc-attach --clear-env -n nagios -- {cmd}'.format(cmd=cmd_line[line]), shell=True)

    call('sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart nagios', shell=True)

    logger.info('Nagios actualizado.')


def remove_server(name, file):
    '''
    Elimina un servidor del escenario que ya haya sido anadido antes.

    Args:
        name        nombre del servidor.
        file        VNX File.

    '''

    # Comprobamos que el servidor existe
    removed = False
    if os.path.exists('./.servers_added'):
        servers = pickle.load(open('./.servers_added', 'rb'))
        for i in range(len(servers)):
            if servers[i]['name'] == name:
                servers.remove(servers[i])
                removed = True
                break

        if not removed:
            logger.error('El servidor no existe.')
            sys.exit()

        pickle.dump(servers, open('./.servers_added', 'wb'))

    else:
        logger.error('El servidor no existe.')
        sys.exit() 

    # Destruimos la maquina
    call('sudo vnx -f {file} --destroy'.format(file=file), shell=True, stdout=devnull)

    # Actualizamos el balanceador
    call('sudo lxc-attach --clear-env -n lb -- killall xr', shell=True)
    cmd_line = 'sudo lxc-attach --clear-env -n lb -- xr --server tcp:0:80 -dr'

    for i in range(1, N_SERVERS_DEFAULT + 1):
        cmd_line += ' --backend 10.1.3.1{n}:3000'.format(n=str(i))

    for i in range(len(servers)):
        cmd_line += ' --backend {ip}:3000'.format(ip=servers[i]['lb_ip'])

    cmd_line += ' --web-interface 0:8001 &'

    call(cmd_line, shell=True, stdout=devnull)

    logger.info('Balanceador actualizado.')

    # Actualizamos Nagios
    call('sudo lxc-attach --clear-env -n nagios -- rm /usr/local/nagios/etc/servers/{name}.cfg'.format(name=name), shell=True)
    call('sudo lxc-attach --clear-env -n nagios -- sudo systemctl restart nagios', shell=True)

    logger.info('Nagios actualizado.')


@contextmanager
def timer(name='task', function=logger.info):
    '''
    Funcion auxiliar que sirve  de temporizador.
    '''
    start = time()
    yield start
    end = time()
    function('{} en {} segundos'.format(name, end - start))


def print_progress(iteration, total, prefix='', suffix='', decimals=1, bar_length=100):
    '''
    Call in a loop to create terminal progress bar
    @params:
        iteration   - Required  : current iteration (Int)
        total       - Required  : total iterations (Int)
        prefix      - Optional  : prefix string (Str)
        suffix      - Optional  : suffix string (Str)
        decimals    - Optional  : positive number of decimals in percent complete (Int)
        bar_length  - Optional  : character length of bar (Int)
    '''
    str_format = "{0:." + str(decimals) + "f}"
    percents = str_format.format(100 * (iteration / float(total)))
    filled_length = int(round(bar_length * iteration / float(total)))
    bar = '=' * filled_length + '>' + '-' * (bar_length - filled_length - 1)

    sys.stdout.write('\r%s [%s] %s%s %s' % (prefix, bar, percents, '%', suffix)),

    if iteration == total:
        sys.stdout.write('\n')
    sys.stdout.flush()


if __name__ == '__main__':
    main()
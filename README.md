# Despliegue de un sistema CRM escalable

El objetivo es la creación de un escenario completo de despliegue de una aplicación fiable y escalable que integre los diversos contenidos impartidos en la asignatura.

La aplicación CRM la podemos encontrar en el siguiente [enlace](https://github.com/CORE-UPM/CRM_2017).

## Tabla de contenidos

* [Descripción](#descripción)
* [Arquitectura](#arquitectura)
  * [Firewall](#firewall)
  * [Balanceador de carga](#balanceador-de-carga)
* [Docker](#docker)
* [Uso del script de configuración en Python](#uso-del-script-de-configuración-en-python)
  * [Descarga y preparación del escenario](#descarga-y-preparación-del-escenario)
  * [Script de configuración](#script-de-configuración)
  * [Añadir un servidor](#añadir-un-servidor)
  * [Eliminar un servidor](#eliminar-un-servidor)
  * [Conexión con el servidor de gestion](#conexion-con-el-servidor-de-gestion)
* [Despliegue en la nube](#despliegue-en-la-nube)
* [Autores](#autores)

## Descripción

La aplicación CRM se configurará para que utilice una base de datos PostgreSQL, que correrá en el servidor de bases de datos, y para que almacene las imágenes en el cluster de almacenamiento que se creará utilizando el sistema de ficheros distribuido GlusterFS. El balanceador de carga se ocupará de distribuir la carga entre los tres servidores que soportan la aplicación CRM (S1, S2 y S3) y el cortafuegos de entrada, basado en el software de Linux FirewallBuilder, se ocupará de filtrar todo el tráfico proveniente de Internet y dejar pasar únicamente el destinado a la aplicación.

La arquitectura debe garantizar la escalabilidad de la aplicación, permitiendo ampliar fácilmente el número de servidores dedicados según crezca el número de usuarios. Por ello se parte de un sistema con un número determinado de servidores, pero se prevé añadir servidores (reales o virtuales) según crezca la demanda del servicio.

* El servicio CRM debe estar accesible a los clientes en el puerto estándar de web (80).
* El balanceador debe balancear la carga entre todos los servidores utilizando un algoritmo round-robin.
* El cluster de almacenamiento, que se utilizará para almacenar las imágenes utilizadas por el CRM se debe configurar de forma que utilice GlusterFS y que replique la información entre los tres servidores (nas1, nas2 y nas3).
* La información manejada por el CRM se debe almacenar en el servidor de bases de datos, utilizando PostgreSQL (recomendado) u otro gestor de bases de datos soportado por el CRM. En cualquier caso, debe utilizarse una base de datos externa desplegada en el servidor destinado a tales efectos. Por lo tanto, no puede utilizarse SQLite.
* El firewall debe permitir únicamente el acceso mediante ping y al puerto 80 de TCP de la dirección balanceador de tráfico. Cualquier otro tráfico debe de estar prohibido.

## Arquitectura

En el proyecto se utilizarán los elementos típicos de las arquitecturas actuales: firewall, balanceador de carga, servidores font-end corriendo la aplicación, bases de datos y servidores de almacenamiento, tal y como aparece representado en la siguiente figura.

![architecture](docs/architecture.png)

La solución que se ha implementado proporciona una **alta disponibilidad**, y es fácilmente **escalable**, aunque se podría conseguir mayor disponibilidad replicando la base de datos postgres. La función y configuración de cada uno de los elementos que forman la arquitectura es la siguiente,

* **FW**, es un cortafuegos y únicamente permite cierto tráfico, el resto queda bloqueado. 
* **LB**, es el balanceador de carga *Crossroads* que balancea el tráfico entre los servidores utilizando el algoritmo round-robin. También realiza un mapeo del puerto 3000 donde corre la aplicación al puerto 80.
* **S1, S2 y S3**, es el servicio en que se aloja la aplicación web CRM. Esta está alojada en el puerto 3000, y es el balanceador de carga el que se encarga de hacer un mapeo del puerto 80 al 3000.
* **BBDD**, es el servicio en que se aloja la base de datos, y utiliza la imagen de Postgres para ello. Para la conexión de la base de datos, utilizamos la siguiente URL, `postgres://crm:xxxx@10.1.4.31:5432/crm`.
* **NAS**, son los servidores de almacenamiento. La información está replicada entre los tres servidores, de forma que se puede leer y escribir en cualquiera de ellos.

Además del escenario original, podemos encontrar una nueva **red de gestión**, desde la cual se puede gestionar y monitorizar todo el sistema.

* **GES**, servidor de gestión al cual nos podemos conectar mediante ssh desde fuera del firewall. Unicamente nos podemos conectar utilizando una clave RSA, el acceso por contraseña queda bloqueado.
* **Nagios**, servidor que corre [Nagios](https://www.nagios.org/), una herramienta de monitorización *open source* que permite monitorizar los equipos y sus servicios de forma remota con un navegador web. Para ello, se utiliza el plugin [NRPE](https://github.com/NagiosEnterprises/nrpe) que se instala en el resto de contenedores y permiten que el servidor central de Nagios monitorice cada uno de ellos. La direccion web para conectarmos al servidor es `10.1.5.52/nagios`. El usuario y contraseña que se establecen por defecto son `nagiosadmin` y `xxxx`.

### Firewall

El firewall únicamente va a permitir el tráfico necesario, además del que se incluía por defecto en el enunciado.

* Se permite conexión vía `ssh` al servidor de gestión GES.
* Se permite conexión `http` al balanceador de tráfico y a la interfaz de monitorización de Nagios.
* Se permite la conexión al firewall al puerto 5666 que es el puerto con el trabaja el plugin *nrpe* de Nagios. Esta regla es para poder monitorizar el estado del servidor que alberga el firewall

> Con el fin de poder ver el balanceo de tráfico, está habilitado el acceso al puerto 8001 del balanceador. En un escenario real, esta regla tendría que ser eliminada.

Para comprobar el funcionamiento del firewall se puede realizar un escaneo de puertos como el que podemos ver en la siguiente [imagen](docs/nmap.png). A continuación se incluye la salida del comando.

```shell
[*] exec: nmap 10.1.0.0/16

Starting Nmap 7.01 ( https://nmap.org ) at 2018-01-13 23:30 CET
Nmap scan report for 10.1.1.2
Host is up (0.00030s latency).
Not shown: 998 closed ports
PORT    STATE SERVICE
22/tcp  open  ssh
111/tcp open  rpcbind

Nmap scan report for 10.1.1.11
Host is up (0.00029s latency).
Not shown: 998 closed ports
PORT    STATE SERVICE
22/tcp  open  ssh
111/tcp open  rpcbind

Nmap scan report for 10.1.1.12
Host is up (0.000071s latency).
Not shown: 998 closed ports
PORT    STATE SERVICE
22/tcp  open  ssh
111/tcp open  rpcbind

Nmap scan report for 10.1.2.2
Host is up (0.00034s latency).
Not shown: 998 filtered ports
PORT     STATE SERVICE
80/tcp   open  http
8001/tcp open  vcom-tunnel

Nmap scan report for 10.1.5.52
Host is up (0.00057s latency).
Not shown: 999 filtered ports
PORT   STATE SERVICE
80/tcp open  http

Nmap done: 65536 IP addresses (5 hosts up) scanned in 2560.20 seconds
```

Del escaneo de puertos, podemos comprobar que el balanceador de tráfico tiene abiertos los puertos 80 y 8001, tal y como hemos definido en las reglas del firewall. El servidor Nagios también tiene abierto el puerto 80. Los otros tres hosts que aparecen, son el propio host y los clientes C1 y C2.

### Balanceador de carga

Para configurar el balanceador una vez operativo se pueden seguir varias opciones para redirigir al mismo cliente al mismo servidor en una conexión, y así que las cookies se mantengan sobre el mismo servidor:

* Se puede declarar el servidor como HTTP en lugar de como TCP y activar la opción *sticky*. Sin embargo, la opción HTTP no está recomendada, ya que el servidor es más eficiente cuando puede manejar también más peticiones de tipo TCP, que sólo HTTP. Cuando el balanceador está en modo HTTP, necesita ejecutar más procesos y el balanceo de tráfico no es óptimo.
* Se puede cambiar el algoritmo de balanceo, aunque para esto hay que relanzar el proceso:
  * Se puede utilizar el algoritmo *lax-hashed-ip* que calcula el *hash* de una IP y la asigna a un servidor del backend, de forma que una misma IP siempre será atendida por el mismo servidor.
  * Se puede utilizar el algoritmo *lax-stored-ip* que cuando un cliente se conecta por primera vez, lo almacena en memoria y le redirige al mismo servidor todo el tiempo hasta que el cliente deje de conectarse durante un tiempo *timeout*. Este algoritmo es menos eficiente que el anterior, ya que requiere de almacenamiento en memoria.

Sin embargo, la mejor opción es que los servidores compartan entre sí las cookies y aunque cambies de servidor, éstas sean reconocidas por el nuevo. Con está última opción, el balanceador de carga podría funcionar en TCP y se podría elegir cualquier tipo de algoritmo.

## Docker

Otra opción es desplegar el escenario con Docker. Para ello se facilitan los Dockerfile necesarios para construir las imágenes y un fichero de configuración para [Docker Compose](https://docs.docker.com/compose/) que permite desplegar el escenario entero con un sólo comando. 

La arquitectura que se ha seguido para implementar Docker es la siguiente.

![docker architecture](docs/docker.png)

En este caso, se han reducido el número de contenedores en comparación con el número de máquinas virtuales necesarias para el despliegue.

* **LB**, es el balanceador de carga *Crossroads* que balancea el tráfico entre los servidores utilizando el algoritmo round-robin. También realiza un mapeo del puerto 3000 donde corre la aplicación al puerto 80. Además, se ha configurado un cortafuegos en el propio contenedor que sólo permite el acceso a los puertos 80 y 8001 mediante tcp.
* **S1, S2 y S3**, es el servicio en que se aloja la aplicación web CRM. Esta está alojada en el puerto 3000, y es el balanceador de carga el que se encarga de hacer un mapeo del puerto 80 al 3000.
* **BBDD**, es el servicio en que se aloja la base de datos, y utiliza la imagen de Postgres para ello. Para la conexión de la base de datos, se utiliza la siguiente URL, `postgres://crm:xxxx@10.1.4.31:5432/crm`.
* **NAS**, son los servidores de almacenamiento. La información está replicada entre los tres servidores, de forma que se puede leer y escribir en cualquiera de ellos.
* **Nagios**, se encarga de la monitorización de todo el escenario. Para ello, se utiliza el plugin NRPE que se instala en el resto de contenedores y permiten que el servidor central de Nagios monitorice cada uno de ellos. Además, se ha configurado un cortafuegos en el propio contenedor que sólo permite el acceso al puerto 80 mediante tcp y al puerto 5666 para el funcionamiento del plugin NRPE.

Para desplegar el escenario, únicamente necesitamos un equipo que tenga Docker y Docker Compose instalados. Una vez instalados y clonado el repositorio, ejecutamos desde el directorio principal el siguiente comando:

```shell
docker-compose up --build
```

Una vez terminado de ejecutar el comando anterior, ya podemos acceder a la aplicación y a la monitorización, para ello desde el navegador entramos a `localhost:<port>` donde el puerto puede ser:

| Puerto | Servicio | 
| -- | -- |
| `8080` | Aplicación del CRM | 
| `8081` | Interfaz de gestión del balanceador | 
| `8085` | Interfaz de monitorización de Nagios. El usuario y contraseña por defecto son `nagiosadmin` y `xxxx`. | 

## Uso del script de configuración en Python

### Descarga y preparación del escenario

La última versión del escenario está disponible en el siguiente [enlace](https://github.com/tasiomendez/cdps-crm/releases).

1. **Si utiliza ordenador propio con VirtualBox**, descargue la máquina virtual a su ordenador desde este [enlace](http://idefix.dit.upm.es/cdps/CDPS2017-v1.ova), e impórtela a VirtualBox y arranquela. Una vez importada, accede a un terminal de la máquina virtual y descargue y descomprima el escenario mediante:

```shell
wget https://github.com/tasiomendez/cdps-crm/releases/download/v1.0.1/pfinal.tgz
sudo vnx --unpack pfinal.tgz && cd pfinal
bin/prepare-pfinal-vm
```

2. **Si utiliza ordenador propio con Linux y VNX**, accede a un terminal, descargue el escenario y descomprímalo mediante:

```shell
wget https://github.com/tasiomendez/cdps-crm/releases/download/v1.0.1/pfinal.tgz
sudo vnx --unpack pfinal.tgz && cd pfinal
bin/prepare-pfinal-vm
```

3. **Si utiliza el laboratorio**, entre en su cuenta, acceda a un terminal, descargue el escenario y descomprímalo.

```shell
wget https://github.com/tasiomendez/cdps-crm/releases/download/v1.0.1/pfinal.tgz
sudo vnx --unpack pfinal.tgz && cd pfinal
bin/prepare-pfinal-labo
```

> Por restricciones de espacio en el laboratorio es necesario trabajar en el directorio /mnt/tmp.

### Script de configuración

El script de configuración te permite automatizar el despliegue del CRM con todos los equipos configurados y listos para usarse. Para ello, una vez que hemos descargado el escenario y lo tenemos todo preparado ejecutamos el script de la siguiente forma:

```python config.py FILE [--create | --destroy | --add-server | --remove-server] [--no-console]```

A continuación, tenemos una breve explicación de las opciones disponibles.

* `FILE`. Archivo que contiene toda la arquitectura del despliegue. Es un archivo XML que se encuentra dentro del escenario.
* `--create`. Crea el escenario y realiza toda la configuración.
* `--destroy`. Elimina el escenario y con ellos, todos los cambios realizados.
* `--add-server`. Añade un servidor extra donde alojar la aplicación y ejecuta todos los cambios necesarios.
* `--remove-server`. Elimina un servidor que haya sido añadido anteriormente.
* `--no-console`. Se puede usar con `--create` o `--add-server`. Al arrancar el escenario no se muestran las consolas de todas las máquinas virtuales. Opcional.

Para destruir el escenario, tenemos que utilizar el archivo del escenario principal. El propio script almacena los servidores que han sido añadidos en un archivo externo y los eliminará forma automática.

### Añadir un servidor

Para añadir un servidor, tenemos que declarar un archivo de tipo XML como el que podemos encontrar en la carpeta [examples](examples). Tenemos que conectarlos a la LAN3, la LAN4 y a la LAN5 para la monitorización, asi como crearla con los archivos necesarios para la instalación de Nagios.

Con esto se pueden añadir tantos servidores como uno quiera, haciéndose las configuraciones mínimas en cada uno de ellos de forma automática, lo que hace que el sistema sea **fácilmente escalable** en función de la carga que tengan que soportar los servidores.

### Eliminar un servidor

Para eliminar un servidor, tenemos que utilizar el mismo archivo XML que utilizamos para crearlo. Al eliminarlo, se actualizará Nagios y el balanceador.

De esta forma, el escenario no sólo es escalable a la hora de añadir servidores, sino también a la hora de eliminarlos.

### Conexión con el servidor de gestion

Para conectarnos con el servidor de gestión tenemos que utilizar la clave que genera el script con el nombre `ges_rsa`. En el caso de existir una clave RSA con ese mismo nombre en la carpeta `~/.ssh/`, el script de configuración pasara a utilizar dicha clave.

Una vez que tenemos localizada la clave nos podemos conectar directamente al servidor haciendo:

```shell
ssh root@ges
```

En el caso de que se nos deniegue el acceso podemos proceder a indicarle el archivo donde se aloja la clave:

```shell
ssh root@ges -i ~/.ssh/ges_rsa
```

Si esto ultimo nos da error, entonces se debe a que la clave no es conocida por el `ssh-agent`. En este caso para solucionar el problema ejecutamos los siguientes comandos:

```shell
ssh-add ~/.ssh/ges_rsa
ssh root@ges
```

## Despliegue en la nube

Este mismo escenario puede ser desplegado en la nube, utilizando varios servicios existentes como pueden ser [Amazon Web Services](https://aws.amazon.com/), [OpenStack](https://www.openstack.org/) o [Google Cloud](https://cloud.google.com/).

Para desplegar el escenario en esos servicios podemos utilizar este escenario y hacerlo sólo en una máquina virtual. Sin embargo esto no es eficiente, ya que los servicios anteriormente nombrados nos ofrecen otras opciones que pueden llegar a ser una mejor solución.

En Amazon Web Services (AWS) tenemos la posibilidad de adquirir ciertos productos que nos hacen la función del firewall o del balanceador de tráfico como pueden ser AWS WAF (Web Application Firewall) o Elastic Load Balancing. Además nos ofrecen sistemas de almacenamiento dinámicos, así como escalabilidad en el número de instancias que queremos ejecutándose en un momento dado. De esta forma, tendríamos que desplegar la aplicación utilizando sus servicios de computación EC2 y preocuparnos de adquirir el resto de servicios necesarios de todos los productos disponibles, así como realizar las conexiones oportunas entre ellos. 

En OpenStack, al igual que en AWS, tenemos varios servicios configurables como Swift para el almacenamiento o Trove para la base de datos. Lo más importante es el uso de Nova, que es el motor va a soportar los contenedores LXC. Además, con Horizon tenemos una interfaz gráfica para el acceso, la provisión y la automatización de los recursos basados en la nube.

> En todos ellos tenemos la opción de utilizar Docker en lugar de contenedores LXC, utilizando Amazon Elastic Container Service en AWS, directamente sobre Nova en OpenStack o con Kubernetes Engine en Google Cloud.

## Autores

Esta práctica ha sido realizada por [Tasio Méndez Ayerbe](https://github.com/tasiomendez/).

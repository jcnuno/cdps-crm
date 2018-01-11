# Despliegue de un sistema CRM escalable

El objetivo es la creación de un escenario completo de despliegue de una aplicación fiable y escalable que integre los diversos contenidos impartidos en la asignatura.

La aplicación CRM la podemos encontrar en el siguiente [enlace](https://github.com/CORE-UPM/CRM_2017).

## Tabla de contenidos

* [Descripción](#descripción)
* [Arquitectura](#arquitectura)
* [Uso](#uso)
  * [Descarga y preparación del escenario](#descarga-y-preparación-del-escenario)
  * [Script de configuración](#script-de-configuración)
  * [Añadir un servidor](#añadir-un-servidor)
  * [Conexión con el servidor de gestion](#conexion-con-el-servidor-de-gestion)
* [Autores](#autores)

## Descripción

La aplicación CRM se configurará para que utilice una base de datos PostgreSQL, que correrá en el servidor de bases de datos, y para que almacene las imágenes en el cluster de almacenamiento que se creará utilizando el sistema de ficheros distribuido GlusterFS. El balanceador de carga se ocupará de distribuir la carga entre los tres servidores que soportan la aplicación CRM (S1, S2 y S3) y el cortafuegos de entrada, basado en el software de Linux FirewallBuilder, se ocupará de filtrar todo el tráfico proveniente de Internet y dejar pasar únicamente el destinado a la aplicación.

La arquitectura debe garantizar la escalabilidad de la aplicación, permitiendo ampliar fácilmente el número de servidores dedicados según crezca el número de usuarios. Por ello se parte de un sistema con un número determinado de servidores, pero se prevé añadir servidores (reales o virtuales) según crezca la demanda del servicio.

* El servicio CRM debe estar accesible a los clientes en el puerto estándar de web (80).
* El balanceador debe balancear la carga entre todos los servidores utilizando un algoritmo round-robin.
* El cluster de almacenamiento, que se utilizará para almacenar las imágenes utilizadas por el CRM se debe configurar de forma que utilice GlusterFS y que replique la información entre los tres servidores (nas1, nas2 y nas3).
* La información manejad por el CRM se debe almacenar en el servidor de bases de datos, utilizando PostgreSQL (recomendado) u otro gestor de bases de datos soportado por el CRM. En cualquier caso, debe utilizarse una base de datos externa desplegada en el servidor destinado a tales efectos. Por lo tanto, no puede utilizarse SQLite.
* El firewall debe permitir únicamente el acceso mediante ping y al puerto 80 de TCP de la dirección balanceador de tráfico. Cualquier otro tráfico debe de estar prohibido.

## Arquitectura

En el proyecto se utilizarán los elementos típicos de las arquitecturas actuales: firewall, balanceador de carga, servidores font-end corriendo la aplicación, bases de datos y servidores de almacenamiento, tal y como aparece representado en la siguiente figura.

![architecture](docs/architecture.png)

La solución que se ha implementado proporciona una **alta disponibilidad**, y es fácilmente **escalable**. 

* **FW**, es un cortafuegos y únicamente permite el acceso mediante ping y al puerto 80 de TCP de la dirección del balanceador de tráfico. Tambien permite el acceso a la direccion web de Nagios para monitorizar todo el sistema y el acceso por ssh al servidor de gestion. El resto de tráfico está bloqueado.
* **LB**, es el balanceador de carga *Crossroads* que balancea el tráfico entre los servidores utilizando el algoritmo round-robin.
* **S1, S2 y S3**, es el servicio en que se aloja la aplicación web CRM. Esta está alojada en el puerto 3000, y es el balanceador de carga el que se encarga de hacer un mapeo del puerto 80 al 3000.
* **BBDD**, es el servicio en que se aloja la base de datos, y utiliza la imagen de Postgres para ello. Para la conexión de la base de datos, utilizamos la siguiente URL, `postgres://crm:xxxx@10.1.4.31:5432/crm`.
* **NAS**, son los servidores de almacenamiento. La información está replicada entre los tres servidores, de forma que se puede leer y escribir en cualquiera de ellos.

Además del escenario original, podemos encontrar una nueva **red de gestión**, desde la cual se puede gestionar y monitorizar todo el sistema.

* **GES**, servidor de gestión al cual nos podemos conectar mediante ssh desde fuera del firewall. Unicamente nos podemos conectar utilizando una clave RSA, el acceso por contraseña queda bloqueado.
* **NAGIOS**, servidor que corre [Nagios](https://www.nagios.org/), una herramienta de monitorización *open source* que permite monitorizar los equipos y sus servicios de forma remota con un navegador web. La direccion web para conectarmos al servidor es `10.1.5.52/nagios`. El usuario y contraseña que se establecen por defecto son `nagiosadmin` y `xxxx`.

Con el script de configuración que está descrito más abajo, se pueden añadir tantos servidores como uno quiera, haciéndose las configuraciones necesarias en cada uno de ellos, lo que hace que el sistema sea fácilmente escalable en función de la carga que tengan que soportar los servidores.

## Uso

### Descarga y preparación del escenario

La última versión del escenario está disponible en el siguiente [enlace](https://github.com/tasiomendez/cdps-crm/releases).

1. **Si utiliza ordenador propio con VirtualBox**

    * Descargue la máquina virtual a su ordenador desde este [enlace](http://idefix.dit.upm.es/cdps/CDPS2017-v1.ova), e impórtela a VirtualBox y arranquela.

    * Accede a un terminal de la máquina virtual y descargue y descomprima el escenario.

    ```shell
    wget https://github.com/tasiomendez/cdps-crm/releases/download/v0.0.2/pfinal.tgz
    sudo vnx --unpack pfinal.tgz && cd pfinal
    bin/prepare-pfinal-vm
    ```

2. **Si utiliza ordenador propio con Linux y VNX**, accede a un terminal del PC y descargue el escenario y descomprímalo mediante:

    ```shell
    wget https://github.com/tasiomendez/cdps-crm/releases/download/v0.0.2/pfinal.tgz
    sudo vnx --unpack pfinal.tgz && cd pfinal
    bin/prepare-pfinal-vm
    ```

3. **Si utiliza el laboratorio**, entre en su cuenta, acceda a un terminal, descargue el escenario y descomprímalo.

    ```shell
    wget https://github.com/tasiomendez/cdps-crm/releases/download/v0.0.2/pfinal.tgz
    sudo vnx --unpack pfinal.tgz && cd pfinal
    bin/prepare-pfinal-labo
    ```

    > Por restricciones de espacio en el laboratorio es necesario trabajar en el directorio /mnt/tmp.

### Script de configuración

El script de configuración te permite automatizar el despliegue del CRM con todos los equipos configurados y listos para usarse. Para ello, una vez que hemos descargado el escenario y lo tenemos todo preparado ejecutamos el script de la siguiente forma:

```python config.py FILE [--create | --destroy | --add-server] [--no-console]```

A continuación, tenemos una breve explicación de las opciones disponibles.

* `FILE`. Archivo que contiene toda la arquitectura del despliegue. Es un archivo XML que se encuentra dentro del escenario.
* `--create`. Crea el escenario y realiza toda la configuración.
* `--destroy`. Elimina el escenario y con ellos, todos los cambios realizados.
* `--add-server`. Añade un servidor extra donde alojar la aplicación y ejecuta todos los cambios necesarios.
* `--no-console`. Se puede usar con `--create` o `--add-server`. Al arrancar el escenario no se muestran las consolas de todas las máquinas virtuales. Opcional.

Para destruir el escenario entero, no sólo tenemos que hacer `--destroy` sobre el XML del escenario principal, sino también sobre los XMLs de los servidores que hemos ido añadiendo.

### Añadir un servidor

Para añadir un servidor, tenemos que declarar un archivo de tipo XML como el que podemos encontrar en la carpeta [examples](examples). Tenemos que conectarlos a la LAN3, la LAN4 y a la LAN5 para la monitorización, asi como crearla con los archivos necesarios para la instalación de Nagios.

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

## Autores

Esta práctica ha sido realizada por [Tasio Méndez Ayerbe](https://github.com/tasiomendez/).

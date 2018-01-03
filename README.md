# Despliegue de un sistema CRM escalable

El objetivo es la creación de un escenario completo de despliegue de una aplicación fiable y escalable que integre los diversos contenidos impartidos en la asignatura.

La aplicación CRM la podemos encontrar en el siguiente [enlace](https://github.com/CORE-UPM/CRM_2017).

## Tabla de contenidos

* [Descripción](#descripción)
* [Arquitectura](#arquitectura)
* [Uso](#uso)
  * [Descarga y preparación del escenario](#descarga-y-preparación-del-escenario)
  * [Script de configuración](#script-de-configuración)
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

![stage](stage.png)

La solución que se ha implementado proporciona una **alta disponibilidad**, y es fácilmente **escalable**.

* **FW**, es un cortafuegos y únicamente permite el acceso mediante ping y al puerto 80 de TCP de la dirección del balanceador de tráfico. El resto de tráfico está bloqueado.
* **LB**, es el balanceador de carga *Crossroads* que balancea el tráfico entre los servidores utilizando el algoritmo round-robin.
* **S1, S2 y S3**, es el servicio en que se aloja la aplicación web CRM. Esta está alojada en el puerto 3000, y es el balanceador de carga el que se encarga de hacer un mapeo del puerto 80 al 3000.
* **BBDD**, es el servicio en que se aloja la base de datos, y utiliza la imagen de Postgres para ello. Para la conexión de la base de datos, utilizamos la siguiente URL, `postgres://crm:xxxx@10.1.4.31:5432/crm`.
* **NAS**, son los servidores de almacenamiento. La información está replicada entre los tres servidores, de forma que se puede leer y escribir en cualquiera de ellos.

## Uso

### Descarga y preparación del escenario

La última versión del escenario está disponible en el siguiente [enlace](https://github.com/tasiomendez/cdps-crm/releases).

1. **Si utiliza ordenador propio con VirtualBox**

    * Descargue la máquina virtual a su ordenador desde este [enlace](http://idefix.dit.upm.es/cdps/CDPS2017-v1.ova), e impórtela a VirtualBox y arranquela.

    * Accede a un terminal de la máquina virtual y descargue y descomprima el escenario.

    ```shell
    wget https://github.com/tasiomendez/cdps-crm/releases/download/0.0.1/pfinal.tgz
    sudo vnx --unpack pfinal.tgz && cd pfinal
    bin/prepare-pfinal-vm
    ```

2. **Si utiliza ordenador propio con Linux y VNX**, accede a un terminal del PC y descargue el escenario y descomprímalo mediante:

    ```shell
    wget https://github.com/tasiomendez/cdps-crm/releases/download/0.0.1/pfinal.tgz
    sudo vnx --unpack pfinal.tgz && cd pfinal
    bin/prepare-pfinal-vm
    ```

3. **Si utiliza el laboratorio**, entre en su cuenta, acceda a un terminal, descargue el escenario y descomprímalo.

    ```shell
    wget https://github.com/tasiomendez/cdps-crm/releases/download/0.0.1/pfinal.tgz
    sudo vnx --unpack pfinal.tgz && cd pfinal
    bin/prepare-pfinal-labo
    ```

    > Por restricciones de espacio en el laboratorio es necesario trabajar en el directorio /mnt/tmp.

### Script de configuración

El script de configuración te permite automatizar el despliegue del CRM con todos los equipos configurados y listos para usarse. Para ello, una vez que hemos descargado el escenario y lo tenemos todo preparado ejecutamos el script de la siguiente forma:

```python config.py FILE (--create | --destroy) [--no-console]```

A continuación, tenemos una breve explicación de las opciones disponibles.

| Opción | Descripción |
| -- | -- | 
| `FILE` | Archivo que contiene toda la arquitectura del despliegue. Es un archivo XML que se encuentra dentro del escenario. |
| `--create` | Crea el escenario y realiza toda la configuración. |
| `--destroy` | Elimina el escenario y con ellos, todos los cambios realizados. |
| `--no-console` | Se usa con `--create`. Al arrancar el escenario no se muestran las consolas de todas las máquinas virtuales. Opcional. |

## Autores

Esta práctica ha sido realizada por [Tasio Méndez Ayerbe](https://github.com/tasiomendez/).

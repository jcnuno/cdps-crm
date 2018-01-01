# Despliegue de un sistema CRM escalable

El objetivo es la creación de un escenario completo de despliegue de una aplicación fiable y escalable que integre los diversos contenidos impartidos en la asignatura.

La aplicación CRM la podemos encontrar en el siguiente [enlace](https://github.com/CORE-UPM/CRM_2017).

## Descripción

En el proyecto se utilizarán los elementos típicos de las arquitecturas actuales: firewall, balanceador de carga, servidores font-end corriendo la aplicación, bases de datos y servidores de almacenamiento, tal y como aparece representado en la siguiente figura.

![stage](stage.png)

La aplicación CRM se configurará para que utilice una base de datos PostgreSQL, que correrá en el servidor de bases de datos, y para que almacene las imágenes en el cluster de almacenamiento que se creará utilizando el sistema de ficheros distribuido GlusterFS. El balanceador de carga se ocupará de distribuir la carga entre los tres servidores que soportan la aplicación CRM (S1, S2 y S3) y el cortafuegos de entrada, basado en el software de Linux FirewallBuilder, se ocupará de filtrar todo el tráfico proveniente de Internet y dejar pasar únicamente el destinado a la aplicación.

La arquitectura debe garantizar la escalabilidad de la aplicación, permitiendo ampliar fácilmente el número de servidores dedicados según crezca el número de usuarios. Por ello se parte de un sistema con un número determinado de servidores, pero se prevé añadir servidores (reales o virtuales) según crezca la demanda del servicio.

* El servicio CRM debe estar accesible a los clientes en el puerto estándar de web (80).
* El balanceador debe balancear la carga entre todos los servidores utilizando un algoritmo round-robin.
* El cluster de almacenamiento, que se utilizará para almacenar las imágenes utilizadas por el CRM se debe configurar de forma que utilice GlusterFS y que replique la información entre los tres servidores (nas1, nas2 y nas3).
* La información manejad por el CRM se debe almacenar en el servidor de bases de datos, utilizando PostgreSQL (recomendado) u otro gestor de bases de datos soportado por el CRM. En cualquier caso, debe utilizarse una base de datos externa desplegada en el servidor destinado a tales efectos. Por lo tanto, no puede utilizarse SQLite.
* El firewall debe permitir únicamente el acceso mediante ping y al puerto 80 de TCP de la dirección balanceador de tráfico. Cualquier otro tráfico debe de estar prohibido.

## Puesta en marcha del escenario

1. **Si utiliza ordenador propio con VirtualBox**

  * Descargue la máquina virtual a su ordenador desde este [enlace](http://idefix.dit.upm.es/cdps/CDPS2017-v1.ova), e impórtela a VirtualBox y arranquela.

  * Accede a un terminal de la máquina virtual y descargue y descomprima el escenario.
    ```shell
    wget https://github.com/tasiomendez/cdps/releases/download/0.0.1/pfinal-with-rootfs.tgz
    sudo vnx --unpack pfinal-with-rootfs.tgz && cd pfinal-with-rootfs
    bin/prepare-pfinal-vm
    ```

2. **Si utiliza ordenador propio con Linux y VNX**, accede a un terminal del PC y descargue el escenario y descomprímalo mediante:

  ```shell
  wget https://github.com/tasiomendez/cdps/releases/download/0.0.1/pfinal-with-rootfs.tgz
  sudo vnx --unpack pfinal-with-rootfs.tgz && cd pfinal-with-rootfs
  bin/prepare-pfinal-vm
  ```

3. **Si utiliza el laboratorio**, entre en su cuenta, acceda a un terminal, descargue el escenario y descomprímalo.

  ```shell
  wget https://github.com/tasiomendez/cdps/releases/download/0.0.1/pfinal-with-rootfs.tgz
  sudo vnx --unpack pfinal-with-rootfs.tgz && cd pfinal-with-rootfs
  bin/prepare-pfinal-labo
  ```

  > Por restricciones de espacio en el laboratorio es necesario trabajar en el directorio /mnt/tmp.

Finalmente, para todas las opciones, copie el script de configuración en la carpeta `pfinal` que se ha creado al montar el escenario y ejecute el script como:

```python config.py```

## Autores

Esta práctica ha sido realizada por [Tasio Méndez Ayerbe](https://github.com/tasiomendez/).

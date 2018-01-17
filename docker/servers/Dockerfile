FROM node:carbon

RUN apt-get update
RUN apt-get install -y git curl glusterfs-client

RUN git clone https://github.com/CORE-UPM/CRM_2017.git
WORKDIR CRM_2017

RUN npm install -y

RUN mkdir -p /mnt/nas/
RUN ln -s /mnt/nas public/uploads

EXPOSE 3000

EXPOSE 111 24007 24008 2049 38465 38466 38467 49152 49153 49514

CMD npm run-script supervisor

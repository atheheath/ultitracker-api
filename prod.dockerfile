FROM python:3.7

RUN apt-get update

RUN apt-get install -y \
    vim \
    git \ 
    nmap \
    postgresql-client 
    # ffmpeg

RUN tempFolder=$(mktemp -d) && \
    currentDir=$(pwd) && \
    cd ${tempFolder} && \
    wget https://github.com/vot/ffbinaries-prebuilt/releases/download/v4.2.1/ffmpeg-4.2.1-linux-64.zip && \
    unzip ffmpeg-4.2.1-linux-64.zip -d ffmpeg && \
    cp ffmpeg/ffmpeg /usr/bin/ && \
    wget https://github.com/vot/ffbinaries-prebuilt/releases/download/v4.2.1/ffprobe-4.2.1-linux-64.zip && \
    unzip ffprobe-4.2.1-linux-64.zip -d ffprobe && \
    cp ffprobe/ffprobe /usr/bin/ && \
    cd ${currentDir}

# install ultitrackerapi python package dependencies
ADD ./ultitrackerapi/requirements.txt /tmp/requirements.txt
RUN pip install -r /tmp/requirements.txt

ADD ./ultitrackerapi /root/ultitrackerapi
WORKDIR /root/ultitrackerapi
RUN python setup.py install

RUN chmod u+x /root/ultitrackerapi/scripts/docker/*

EXPOSE 80 443
ENV SERVER_API_PORT=3001
ENV SERVER_IMAGE_PORT=6789
ENV FASTAPI_MODULE=app.main:app

CMD ["bash", "/root/ultitrackerapi/scripts/docker/docker_start_uvicorn_prod.sh"]

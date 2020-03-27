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

# # Add python application to root folder
# RUN mv ./app /app

# WORKDIR /

# # run unittests
# RUN python -m unittest tests

# # copy in and install python requirements.txt
# COPY ./requirements.txt /tmp/requirements.txt
# RUN pip install -r /tmp/requirements.txt

# RUN ls /app

# # From https://github.com/nginxinc/docker-nginx/blob/1fe92b86a3c3a6482c54a0858d1fcb22e591279f/mainline/stretch/Dockerfile
# CMD ["nginx", "-g", "daemon off;"]
# # CMD ["nginx", "-c", "/etc/nginx/sites-available/uvicorn_nginx.conf", "-g", "daemon off;"]

# # Deploy FastApi
# CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "3000"]

# Start nginx and uvicorn
RUN chmod u+x /root/ultitrackerapi/scripts/docker/*

ENV SERVER_API_PORT=3001
ENV SERVER_IMAGE_PORT=6789
ENV FASTAPI_MODULE=app.main:app

# Get aws credentials in there
ADD ./.aws/credentials /root/.aws/credentials
ADD ./.aws/config /root/.aws/config

CMD ["bash", "/root/ultitrackerapi/scripts/docker/docker_start_uvicorn_dev.sh"]

# init a base image(ubuntu linux)
FROM python:latest

RUN apt-get update \
    && apt-get install tesseract-ocr -y \
    && apt-get install -y libleptonica-dev \
    && apt-get install -y pkg-config \
    && apt-get install -y libswscale-dev \
    && apt-get install -y libtbb2 \
    && apt-get install -y libtbb-dev \
    && apt-get install -y libjpeg-dev \
    && apt-get install -y libpng-dev \
    && apt-get install -y libtiff-dev \
    && apt-get install -y libavformat-dev \
    && apt-get install -y libpq-dev \
    #python3.8 \
    #python-setuptools \
    #python3-pip \
    && python3 -m pip install --upgrade pip \
    && apt-get clean \
    && apt-get autoremove
# define the current working directory
WORKDIR /flask-api
# copy the contents into the working directory
ADD . /flask-api
#run pip to install the dependencies of the flask app
RUN pip3 install -r requirements.txt
RUN chmod +x gunicorn.sh
#define the command to start the container
ENTRYPOINT [ "./gunicorn.sh" ]


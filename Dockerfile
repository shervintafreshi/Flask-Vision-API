# init a base image(ubuntu linux)
FROM python:latest

RUN apt-get update \
    && apt-get install tesseract-ocr -y \
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



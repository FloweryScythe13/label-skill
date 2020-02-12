FROM ubuntu:latest
RUN apt-get update -y
RUN apt-get install -y build-essential python3.6 python3.6-dev python3-pip python3.6-venv
# update pip
RUN python3.6 -m pip install pip --upgrade
RUN python3.6 -m pip install wheel

COPY . /app
WORKDIR /app
RUN pip install -r requirements.txt
RUN python3.6 -m spacy download en_core_web_sm
#ENTRYPOINT ["waitress-serve --call'main:create_app'"]

CMD ["waitress-serve", "--call", "main:create_app"]
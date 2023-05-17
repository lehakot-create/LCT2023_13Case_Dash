FROM python:3.8-slim-buster

WORKDIR /app

COPY . /app

EXPOSE 8050

RUN pip install --upgrade pip

RUN pip3 install -r requirements.txt

CMD ["python3", "app_kola.py"]
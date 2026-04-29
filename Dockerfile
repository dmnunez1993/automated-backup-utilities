FROM python:3.12-alpine

RUN apk add postgresql docker mysql-client && rm -rf /var/cache/apk/*

RUN mkdir /app

WORKDIR /app

COPY requirements.txt /app/

RUN pip install -r requirements.txt

COPY . /app/

RUN python -m pytest tests/ -v

CMD [ "python3", "app.py" ]

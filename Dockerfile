FROM python:3.11-alpine as compile-image

RUN apk --no-cache add gcc musl-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt requirements.txt
RUN pip install --user --no-cache-dir -r requirements.txt

FROM python:3.11-alpine as build-image
COPY --from=compile-image /root/.local /root/.local
ENV PATH=/root/.local/bin:$PATH

WORKDIR /app

COPY main.py main.py
COPY src src
COPY config.yaml config.yaml
RUN mkdir logs -p

CMD ["python", "main.py", "-d", "xmpp-prosody"]

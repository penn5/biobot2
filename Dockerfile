FROM python:3-alpine

WORKDIR /app
COPY . .

RUN apk add --update --no-cache --virtual .build-deps \
        g++ \
        python3-dev \
        libxml2 \
        libxml2-dev \
        git && \
    apk add --update --no-cache libxslt-dev && \
    pip install --no-cache-dir -r requirements.txt coloredlogs && \
    apk --no-cache del .build-deps

CMD ["python3", "-m", "biobot"]

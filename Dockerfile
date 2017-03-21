FROM alpine:3.5

ADD . /aws-snapshot-tool

ARG aws_access_key
ARG aws_secret_key

ENV AWS_ACCESS_KEY ${aws_access_key}
ENV AWS_SECRET_KEY ${aws_secret_key}

RUN apk update && apk add python-dev py-pip && \
    pip install --upgrade pip && \
    pip install -r /aws-snapshot-tool/requirements.txt && \
    chmod +x /aws-snapshot-tool/bin/snapshot-daily && \
    cp /aws-snapshot-tool/bin/snapshot-daily /etc/periodic/daily

CMD crond -d 8 -f

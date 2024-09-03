FROM alpine

RUN apk add --update --no-cache netcat-openbsd

COPY ./validate.sh ./
RUN chmod +x validate.sh
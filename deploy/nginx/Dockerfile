FROM nginx:1.27-alpine

RUN apk add --no-cache apache2-utils

COPY deploy/nginx/default.conf.template /etc/nginx/templates/default.conf.template
COPY deploy/nginx/15-create-auth-file.sh /docker-entrypoint.d/15-create-auth-file.sh

RUN chmod 0755 /docker-entrypoint.d/15-create-auth-file.sh

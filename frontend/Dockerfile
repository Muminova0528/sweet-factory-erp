FROM nginx:alpine

COPY index.html /usr/share/nginx/html/index.html

EXPOSE 80

HEALTHCHECK --interval=30s --timeout=5s \
    CMD wget -q -O- http://localhost/index.html || exit 1

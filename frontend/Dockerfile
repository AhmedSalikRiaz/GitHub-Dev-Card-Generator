FROM nginx:alpine

# Copy the index.html
COPY index.html /usr/share/nginx/html/index.template.html

# Default backend URL (can be overridden at runtime)
ENV BACKEND_URL=http://localhost:8080

# Use a shell script to replace the variable and start nginx
CMD ["/bin/sh", "-c", "envsubst '${BACKEND_URL}' < /usr/share/nginx/html/index.template.html > /usr/share/nginx/html/index.html && nginx -g 'daemon off;'"]

EXPOSE 80

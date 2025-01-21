FROM prosody/prosody:latest

COPY prosody.cfg.lua /etc/prosody/
COPY register.lua /register.lua

EXPOSE 80 443 5222 5269 5347 5280 5281

# Install OpenSSL
RUN apt-get update && \
    apt-get install -y openssl

# Generate a self-signed certificate
RUN openssl genrsa -des3 -passout pass:x -out server.pass.key 2048 && \
  openssl rsa -passin pass:x -in server.pass.key -out server.key && \
  rm server.pass.key && \
  openssl req -new -key server.key -out server.csr \
    -subj "/C=NL/ST=Noord Brabant/L=Boxtel/O=Fontys University of Applied Sciences/OU=Software Engineering/CN=xmpp-prosody" && \
  openssl x509 -req -days 365 -in server.csr -signkey server.key -out server.crt

RUN mv server.crt /etc/prosody/certs/server.crt
RUN mv server.key /etc/prosody/certs/server.key

# Fix permissions for certificate
RUN chown -R prosody /etc/prosody/

CMD ["prosody", "-F"]

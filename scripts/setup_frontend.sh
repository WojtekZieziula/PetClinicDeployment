#!/bin/bash
set -euo pipefail
BACKEND_HOST=$1
BACKEND_PORT=${2:-9966}
export DEBIAN_FRONTEND=noninteractive

echo "[FRONTEND] Installing Node.js and Nginx..."
curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
sudo apt-get install -y nodejs nginx git
sudo npm install -g @angular/cli

cd "$HOME"
git clone https://github.com/spring-petclinic/spring-petclinic-angular.git
cd spring-petclinic-angular

sed -i "s|'http://localhost:9966/petclinic/api/'|'/petclinic/api/'|g" src/environments/environment.prod.ts

npm install && ng build --configuration=production --base-href=/petclinic/

sudo mkdir -p /var/www/petclinic
sudo cp -r dist/* /var/www/petclinic/

sudo tee /etc/nginx/sites-available/petclinic.conf > /dev/null <<EOF
server {
    listen 80;
    location /petclinic/ {
        alias /var/www/petclinic/;
        try_files \$uri \$uri/ /petclinic/index.html;
    }
    location /petclinic/api/ {
        proxy_pass http://${BACKEND_HOST}:${BACKEND_PORT}/petclinic/api/;
    }
}
EOF

sudo ln -s /etc/nginx/sites-available/petclinic.conf /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo systemctl restart nginx
echo "[FRONTEND] Nginx configured."

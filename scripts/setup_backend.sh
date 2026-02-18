#!/bin/bash
set -euo pipefail
DB_HOST=$1
DB_PORT=${2:-3306}
APP_PORT=${3:-9966}
DB_USER=${4:-petclinic}
DB_PASS=${5:-petclinic}
DB_NAME=${6:-petclinic}
export DEBIAN_FRONTEND=noninteractive

echo "[BACKEND] Installing Java 17, Git and Maven..."
sudo apt-get update && sudo apt-get install -y openjdk-17-jdk git maven

cd "$HOME"
git clone https://github.com/spring-petclinic/spring-petclinic-rest.git
cd spring-petclinic-rest

echo "[BACKEND] Building application (this will take a moment)..."
./mvnw clean package -DskipTests

JAR_FILE=$(find target -name "spring-petclinic-rest-*.jar" | head -n 1)

sudo tee /etc/systemd/system/petclinic-backend.service > /dev/null <<EOF
[Unit]
Description=Spring Petclinic REST Backend
After=network.target

[Service]
User=$USER
WorkingDirectory=$HOME/spring-petclinic-rest
ExecStart=/usr/bin/java -jar $HOME/spring-petclinic-rest/$JAR_FILE \
    --server.port=${APP_PORT} \
    --spring.profiles.active=mysql,spring-data-jpa \
    --spring.datasource.url=jdbc:mysql://${DB_HOST}:${DB_PORT}/${DB_NAME} \
    --spring.datasource.username=${DB_USER} \
    --spring.datasource.password=${DB_PASS}
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable petclinic-backend
sudo systemctl start petclinic-backend

echo "[BACKEND] Waiting for service to start on port $APP_PORT..."
for i in $(seq 1 30); do
    if ss -tlnp | grep -q ":${APP_PORT}"; then
        echo "[BACKEND] Service is up and listening on port $APP_PORT."
        exit 0
    fi
    if ! systemctl is-active --quiet petclinic-backend; then
        echo "[BACKEND] ERROR: Service crashed. Check: journalctl -u petclinic-backend"
        exit 1
    fi
    sleep 5
done
echo "[BACKEND] ERROR: Service did not start listening within 150 seconds."
exit 1

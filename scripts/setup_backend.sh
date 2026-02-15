#!/bin/bash
DB_HOST=$1
DB_PORT=${2:-3306}
APP_PORT=${3:-9966}
export DEBIAN_FRONTEND=noninteractive

echo "[BACKEND] Installing Java 17, Git and Maven..."
sudo apt-get update && sudo apt-get install -y openjdk-17-jdk git maven

cd /home/azureuser
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
User=azureuser
WorkingDirectory=/home/azureuser/spring-petclinic-rest
ExecStart=/usr/bin/java -jar /home/azureuser/spring-petclinic-rest/$JAR_FILE \
    --server.port=${APP_PORT} \
    --spring.profiles.active=mysql,spring-data-jpa \
    --spring.datasource.url=jdbc:mysql://${DB_HOST}:${DB_PORT}/petclinic \
    --spring.datasource.username=petclinic \
    --spring.datasource.password=petclinic
Restart=always

[Install]
WantedBy=multi-user.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable petclinic-backend
sudo systemctl start petclinic-backend
echo "[BACKEND] Service started on port $APP_PORT."

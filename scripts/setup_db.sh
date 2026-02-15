#!/bin/bash
set -euo pipefail
DATABASE_PORT=${1:-3306}
DB_USER=${2:-petclinic}
DB_PASS=${3:-petclinic}
export DEBIAN_FRONTEND=noninteractive

echo "[DATABASE] Starting configuration on port $DATABASE_PORT..."
sudo apt-get update && sudo apt-get install -y mysql-server

sudo sed -i "s/^bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf
sudo sed -i '/port/d' /etc/mysql/mysql.conf.d/mysqld.cnf
echo "port = $DATABASE_PORT" | sudo tee -a /etc/mysql/mysql.conf.d/mysqld.cnf

sudo systemctl restart mysql

sudo mysql -u root <<MYSQL_SCRIPT
CREATE DATABASE IF NOT EXISTS petclinic;
CREATE USER IF NOT EXISTS '${DB_USER}'@'%' IDENTIFIED BY '${DB_PASS}';
GRANT ALL PRIVILEGES ON petclinic.* TO '${DB_USER}'@'%';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

echo "[DATABASE] Verifying MySQL is accepting connections..."
for i in $(seq 1 10); do
    if mysqladmin ping -h 127.0.0.1 -P "$DATABASE_PORT" --silent 2>/dev/null; then
        echo "[DATABASE] MySQL is up and accepting connections."
        exit 0
    fi
    sleep 2
done
echo "[DATABASE] ERROR: MySQL did not start within 20 seconds."
exit 1

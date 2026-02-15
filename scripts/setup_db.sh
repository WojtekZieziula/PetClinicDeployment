#!/bin/bash
DATABASE_PORT=${1:-3306}
export DEBIAN_FRONTEND=noninteractive

echo "[DATABASE] Starting configuration on port $DATABASE_PORT..."
sudo apt-get update && sudo apt-get install -y mysql-server

sudo sed -i "s/^bind-address.*/bind-address = 0.0.0.0/" /etc/mysql/mysql.conf.d/mysqld.cnf
sudo sed -i '/port/d' /etc/mysql/mysql.conf.d/mysqld.cnf
echo "port = $DATABASE_PORT" | sudo tee -a /etc/mysql/mysql.conf.d/mysqld.cnf

sudo systemctl restart mysql

sudo mysql -u root <<MYSQL_SCRIPT
CREATE DATABASE IF NOT EXISTS petclinic;
CREATE USER IF NOT EXISTS 'petclinic'@'%' IDENTIFIED BY 'petclinic';
GRANT ALL PRIVILEGES ON petclinic.* TO 'petclinic'@'%';
FLUSH PRIVILEGES;
MYSQL_SCRIPT

echo "[DATABASE] Configuration completed."

#!/bin/bash
# =============================================================================
# Rank Tracker — Script de instalación para VPS Ubuntu 22.04
# Ejecutar como root: bash setup.sh
# =============================================================================

set -e  # Parar si hay algún error

APP_DIR="/var/www/ranktracker"
APP_USER="ranktracker"
PYTHON_VERSION="3.11"

echo "======================================================"
echo " Rank Tracker — Instalación en VPS"
echo "======================================================"

# --- 1. Actualizar sistema ---
echo "[1/8] Actualizando sistema..."
apt update && apt upgrade -y

# --- 2. Instalar dependencias del sistema ---
echo "[2/8] Instalando dependencias..."
apt install -y \
    python${PYTHON_VERSION} python${PYTHON_VERSION}-venv python3-pip \
    mysql-server \
    redis-server \
    nginx \
    certbot python3-certbot-nginx \
    git curl ufw

# --- 3. Crear usuario del sistema para la app ---
echo "[3/8] Creando usuario '${APP_USER}'..."
id -u ${APP_USER} &>/dev/null || useradd --system --no-create-home --shell /usr/sbin/nologin ${APP_USER}

# --- 4. Clonar repositorio ---
echo "[4/8] Clonando repositorio..."
mkdir -p ${APP_DIR}
git clone https://github.com/buenroger/ranktracker.git ${APP_DIR} || \
    (cd ${APP_DIR} && git pull)
chown -R ${APP_USER}:${APP_USER} ${APP_DIR}

# --- 5. Crear entorno virtual e instalar dependencias Python ---
echo "[5/8] Instalando dependencias Python..."
python${PYTHON_VERSION} -m venv ${APP_DIR}/.venv
${APP_DIR}/.venv/bin/pip install --upgrade pip
${APP_DIR}/.venv/bin/pip install -r ${APP_DIR}/requirements.txt
${APP_DIR}/.venv/bin/pip install gunicorn

# --- 6. Configurar base de datos MySQL ---
echo "[6/8] Configurando MySQL..."
mysql -e "CREATE DATABASE IF NOT EXISTS ranktracker CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
mysql -e "CREATE USER IF NOT EXISTS 'ranktracker'@'localhost' IDENTIFIED BY 'CAMBIA_ESTA_PASSWORD';"
mysql -e "GRANT ALL PRIVILEGES ON ranktracker.* TO 'ranktracker'@'localhost';"
mysql -e "FLUSH PRIVILEGES;"
mysql ranktracker < ${APP_DIR}/schema.sql
echo "  ⚠ Recuerda cambiar la password de MySQL en /etc/mysql/... y en el .env"

# --- 7. Configurar Redis ---
echo "[7/7] Configurando Redis..."
systemctl enable redis-server
systemctl start redis-server

# --- 8. Copiar archivos de configuración ---
echo "[8/8] Instalando servicios systemd y Nginx..."
cp ${APP_DIR}/deploy/ranktracker-api.service    /etc/systemd/system/
cp ${APP_DIR}/deploy/ranktracker-worker.service /etc/systemd/system/
cp ${APP_DIR}/deploy/ranktracker-beat.service   /etc/systemd/system/
cp ${APP_DIR}/deploy/nginx.conf                 /etc/nginx/sites-available/ranktracker
ln -sf /etc/nginx/sites-available/ranktracker  /etc/nginx/sites-enabled/ranktracker
rm -f /etc/nginx/sites-enabled/default

systemctl daemon-reload
systemctl enable ranktracker-api ranktracker-worker ranktracker-beat

echo ""
echo "======================================================"
echo " Instalación base completada."
echo ""
echo " Próximos pasos:"
echo "   1. Copia tu .env al servidor: scp .env root@TU_IP:/var/www/ranktracker/.env"
echo "   2. Edita /var/www/ranktracker/deploy/nginx.conf con tu dominio"
echo "   3. Ejecuta: bash /var/www/ranktracker/deploy/start.sh"
echo "======================================================"

#!/bin/bash
# =============================================================================
# Rank Tracker — Arrancar / reiniciar todos los servicios
# Ejecutar como root tras configurar el .env y el nginx.conf
# =============================================================================

set -e

APP_DIR="/var/www/ranktracker"

echo "[1/4] Probando configuración Nginx..."
nginx -t

echo "[2/4] Reiniciando Nginx..."
systemctl restart nginx

echo "[3/4] Arrancando API (Gunicorn + Uvicorn)..."
systemctl restart ranktracker-api

echo "[4/4] Arrancando Celery worker y beat..."
systemctl restart ranktracker-worker
systemctl restart ranktracker-beat

echo ""
echo "Estado de los servicios:"
systemctl status ranktracker-api    --no-pager -l | tail -5
systemctl status ranktracker-worker --no-pager -l | tail -5
systemctl status ranktracker-beat   --no-pager -l | tail -5

echo ""
echo "✓ Todo arrancado. Logs:"
echo "  API:    journalctl -u ranktracker-api    -f"
echo "  Worker: journalctl -u ranktracker-worker -f"
echo "  Beat:   journalctl -u ranktracker-beat   -f"

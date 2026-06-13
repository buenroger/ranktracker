# Gunicorn configuration para Rank Tracker API
import multiprocessing

# Dirección y puerto de escucha (Nginx hará de proxy)
bind = "127.0.0.1:8000"

# Workers: 2 × núcleos + 1 (recomendado para I/O async)
workers = multiprocessing.cpu_count() * 2 + 1

# Clase de worker async (requiere uvicorn instalado)
worker_class = "uvicorn.workers.UvicornWorker"

# Timeouts
timeout = 120
keepalive = 5

# Logs
accesslog = "/var/log/ranktracker/access.log"
errorlog  = "/var/log/ranktracker/error.log"
loglevel  = "info"

# Directorio de trabajo
chdir = "/var/www/ranktracker"

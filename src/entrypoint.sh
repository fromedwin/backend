#!/bin/sh

# Disable Python output buffering to prevent log interleaving issues
export PYTHONUNBUFFERED=1

echo "======================================"
echo "ENTRYPOINT SCRIPT STARTING"
echo "DJANGO_SETTINGS_MODULE: $DJANGO_SETTINGS_MODULE"
echo "Hostname: $(hostname)"
echo "Container ID: $(cat /etc/hostname)"
echo "======================================"

if [ "$DJANGO_SETTINGS_MODULE" = "fromedwin.settings.prod" ]; then
  echo "Production mode detected."

  cd /app/src
  echo "Running migrations in PRODUCTION mode..."
  python manage.py migrate || { echo "Migration failed!"; exit 1; }
  echo "✓ Migrations completed"
  
  echo "Collecting static files..."
  python manage.py collectstatic --noinput || { echo "Collectstatic failed!"; exit 1; }
  echo "✓ Static files collected"
  
  echo "======================================"
  echo "ALL SETUP COMPLETED - STARTING GUNICORN"
  echo "======================================"
  exec gunicorn --bind 0.0.0.0:8000 --workers 3 --timeout 120 fromedwin.wsgi:application

else
  echo "Development mode detected."

  if [ -z "$SECRET_KEY" ]; then
    echo "No SECRET_KEY found. Generating a new one..."
    export SECRET_KEY=$(tr -dc 'a-z0-9!@#$%^&*(-_=+)' < /dev/urandom | head -c50)
    echo "SECRET_KEY generated successfully."
  fi

  export COMPRESS_OFFLINE=True

  cd /app/src

  python manage.py compilescss
  python manage.py collectstatic --noinput
  echo "Running migrations in DEVELOPMENT mode..."
  python manage.py migrate

  # gunicorn fromedwin.wsgi:application --bind 0.0.0.0:${PORT:-8000}
  exec python manage.py runserver 0.0.0.0:${PORT:-8000}

fi
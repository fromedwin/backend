# Settings Configuration

FromEdwin Monitor uses a modular Django settings structure that separates configuration based on the deployment environment. This approach provides better security, maintainability, and flexibility across different deployment scenarios.

## Settings Structure

The settings are organized in a dedicated `settings/` package with the following structure:

```
src/settings/
├── __init__.py          # Package initialization and documentation
├── base.py              # Common settings shared across all environments
├── dev.py               # Development-specific settings
└── prod.py              # Production-specific settings
```

## Base Settings (`base.py`)

The base settings file contains all common configuration that applies to every environment:

### Core Django Configuration
- **Application Definition**: All installed apps and middleware
- **Database Configuration**: Default database setup with environment variable support
- **Authentication**: Django and social authentication backends
- **Templates**: Template engine configuration
- **Static Files**: Static file handling and storage backends

### Third-Party Services
- **Celery**: Message queue configuration for background tasks
- **InfluxDB**: Time-series database for metrics storage
- **Sentry**: Error tracking and performance monitoring
- **S3 Storage**: Cloud storage configuration (optional)

### Application-Specific Settings
- **Monitoring Intervals**: Service check frequencies and thresholds
- **Freemium Limits**: Resource limits for free tier users
- **Email Configuration**: SMTP settings and templates
- **Social Authentication**: GitHub OAuth integration

## Development Settings (`dev.py`)

Development settings extend the base configuration with developer-friendly defaults:

### Debug Configuration
```python
DEBUG = True
ALLOWED_HOSTS = ['localhost', '127.0.0.1', '0.0.0.0']
```

### Development Tools
- **Console Email Backend**: Emails are printed to console instead of being sent
- **Synchronous Celery**: Tasks execute immediately for easier debugging
- **Debug Logging**: Verbose logging to console for development

### Database
- **SQLite Default**: Uses local SQLite database when `DATABASE_URL` is not set
- **Django Debug Toolbar**: Available for database query analysis

## Production Settings (`prod.py`)

Production settings prioritize security, performance, and reliability:

### Security Headers
```python
SECURE_SSL_REDIRECT = True
SECURE_HSTS_SECONDS = 31536000
SECURE_HSTS_INCLUDE_SUBDOMAINS = True
SECURE_CONTENT_TYPE_NOSNIFF = True
SECURE_BROWSER_XSS_FILTER = True
X_FRAME_OPTIONS = 'DENY'
```

### Performance Optimizations
- **Redis Caching**: Distributed caching for improved performance
- **Session Storage**: Cache-based session storage
- **Asynchronous Celery**: Background task processing

### Production Logging
- **File Logging**: Structured logging to `/var/log/django/django.log`
- **Error Reporting**: Enhanced error tracking and monitoring
- **Log Rotation**: Automatic log file management

### Required Environment Variables
Production settings validate that critical environment variables are set:
- `DATABASE_URL`: Database connection string
- `EMAIL_HOST`: SMTP server for email delivery
- `SECRET_KEY`: Django secret key (must be secure)

## Environment Variables

### Required for All Environments
```bash
SECRET_KEY=your-secret-key-here
DOMAIN=yourdomain.com
```

### Database Configuration
```bash
DATABASE_URL=postgresql://user:pass@localhost/dbname
```

### Email Configuration
```bash
EMAIL_HOST=smtp.yourdomain.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@yourdomain.com
EMAIL_HOST_PASSWORD=your-password
EMAIL_USE_TLS=True
```

### External Services
```bash
# ShellUI JWT authentication (REST API)
SHELLUI_JWT_ORIGIN=http://localhost:8000
SHELLUI_JWT_ALGORITHMS=RS256,ES256,EdDSA
CORS_ALLOWED_ORIGINS=https://app.fromedwin.com,http://localhost:4000

# Sentry (Error Tracking)
SENTRY_DSN=https://your-sentry-dsn
SENTRY_ENVIRONMENT=production

# InfluxDB (Metrics Storage)
INFLUXDB_URL=http://localhost:8086
INFLUXDB_TOKEN=your-influxdb-token
INFLUXDB_ORG=your-organization
INFLUXDB_BUCKET=your-bucket

# Celery (Message Queue)
CELERY_BROKER_URL=amqp://user:pass@localhost:5672/
CELERY_BROKER_UI_URL=http://localhost:15672

# S3 Storage (Optional)
STORAGE=S3
AWS_ACCESS_KEY_ID=your-access-key
AWS_SECRET_ACCESS_KEY=your-secret-key
AWS_STORAGE_BUCKET_NAME=your-bucket
AWS_S3_CUSTOM_DOMAIN=your-cdn-domain.com
```

## Usage

### Development
```bash
# Set environment variable
export DJANGO_SETTINGS_MODULE=fromedwin.settings.dev

# Run development server
python manage.py runserver

# Run tests
python manage.py test
```

### Production
```bash
# Set environment variable
export DJANGO_SETTINGS_MODULE=fromedwin.settings.prod

# Collect static files
python manage.py collectstatic --noinput

# Run migrations
python manage.py migrate

# Start application server
gunicorn core.wsgi:application
```

### Docker Deployment
```dockerfile
# In your Dockerfile
ENV DJANGO_SETTINGS_MODULE=fromedwin.settings.prod

# Or in docker-compose.yml
environment:
  - DJANGO_SETTINGS_MODULE=fromedwin.settings.prod
```

## Entry Points Configuration

Different Django entry points use appropriate settings:

- **`manage.py`**: Uses `fromedwin.settings.dev` for development commands
- **`core/wsgi.py`**: Uses `fromedwin.settings.prod` for production WSGI server
- **`core/asgi.py`**: Uses `fromedwin.settings.prod` for production ASGI server
- **`core/celery.py`**: Uses `fromedwin.settings.prod` for Celery workers

## Migration from Legacy Settings

If you're upgrading from a previous version with a single `settings.py` file:

1. **Environment Variables**: No changes needed - all environment variables work the same way
2. **Import Statements**: Code using `from django.conf import settings` continues to work unchanged
3. **Custom Settings**: Add any custom settings to the appropriate environment file

## Best Practices

### Security
- Never commit secret keys or passwords to version control
- Use environment variables for all sensitive configuration
- Regularly rotate secret keys and API tokens

### Environment Management
- Use different databases for development and production
- Test production settings in a staging environment
- Monitor application logs for configuration issues

### Performance
- Use Redis caching in production
- Configure appropriate database connection pooling
- Monitor resource usage and adjust limits as needed

## Troubleshooting

### Common Issues

**ImportError: No module named 'settings'**
```bash
# Ensure you're in the correct directory
cd src/
export DJANGO_SETTINGS_MODULE=fromedwin.settings.dev
```

**Database Configuration Error**
```bash
# Check DATABASE_URL format
export DATABASE_URL=postgresql://user:pass@host:port/database
```

**Static Files Not Loading**
```bash
# Collect static files for production
python manage.py collectstatic --noinput
```

### Debugging Configuration
```python
# Check current settings
python manage.py shell
>>> from django.conf import settings
>>> print(settings.DEBUG)
>>> print(settings.DATABASES)
```

## Advanced Configuration

### Custom Environment
To create a custom environment (e.g., staging):

1. Create `fromedwin/settings/staging.py`
2. Import from base settings
3. Override specific configurations
4. Set `DJANGO_SETTINGS_MODULE=fromedwin.settings.staging`

### Configuration Validation
```python
# In your custom settings file
from django.core.exceptions import ImproperlyConfigured

def get_env_variable(var_name):
    """Get environment variable or raise exception."""
    try:
        return os.environ[var_name]
    except KeyError:
        error_msg = f"Set the {var_name} environment variable"
        raise ImproperlyConfigured(error_msg)
```

This modular approach ensures that FromEdwin Monitor can be easily deployed across different environments while maintaining security and performance best practices. 
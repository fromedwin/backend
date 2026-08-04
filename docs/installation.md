# Installation

## How to Run Locally

The application is containerized using Docker Compose and includes all necessary services for a complete monitoring solution. The setup includes:

- **Django Backend**: Main web application running on port 8000
- **RabbitMQ**: Message broker for task queue management
- **PostgreSQL**: Primary application database
- **Celery Workers**: Background task processing
- **Lighthouse Workers**: Web performance monitoring
- **Prometheus & Alertmanager**: Metrics storage, PromQL queries, and alerting
- **Blackbox Exporter**: HTTP/SSL probing for availability

To start the application:

1. Ensure Docker and Docker Compose are installed on your system
2. Clone the repository and navigate to the project directory
3. Run the following command:
   ```bash
   docker compose up
   ```
4. Wait for all services to start (this may take a few minutes on first run)
5. Access the application at `http://localhost:8000`

The application will be fully functional with all monitoring capabilities enabled. Default credentials and configurations are pre-configured for immediate use.


## Deployment

A dedicated deployment guide will be written later in development to explain how to deploy FromEdwin Monitor in production environments.

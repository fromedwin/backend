# Architecture

User interface run as a **django project**. Data are stored in dev mode within **sqlite**, but should be stored on **postgresql** in production.

**Django** create tasks using **celery** and dispatch them using **rabbitMQ**. It runs a **scheduler** to trigger tasks at regular interval. It also run multiple **workers** based on django code base.

A **typescript worker** run multipel replicas to trigger **lighthouse** reports.

Django generate a **prometheus** config file to trigger monitoring using **blackbox** plugin. **Alertmanager** is connected to prometheus and calling back webhooks to django.

**Prometheus** stores time-series metrics (Blackbox probes, RabbitMQ). Django queries Prometheus with PromQL to display availability charts and admin stats.

```{mermaid}
graph TD
    %% Define styles
    classDef infrastructure fill:#e1f5fe,stroke:#01579b,stroke-width:2px
    classDef worker fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px
    classDef monitoring fill:#fff3e0,stroke:#e65100,stroke-width:2px
    classDef scheduler fill:#f3e5f5,stroke:#6a1b9a,stroke-width:2px
    classDef external fill:#f5f5f5,stroke:#616161,stroke-width:1px

    %% Infrastructure Layer
    RabbitMQ[RabbitMQ<br>Message Broker]

    %% Worker Layer
    Celery[Celery Workers<br>Task Processing]
    Lighthouse[Lighthouse Workers<br>Web Performance]
    Heartbeats[Heartbeats Service<br>Config Sync]

    %% Monitoring Layer
    Prometheus[Prometheus<br>Metrics & PromQL]
    Alertmanager[Alertmanager<br>Alert Handling]
    Blackbox[Blackbox Exporter<br>Endpoint Monitoring]

    %% Scheduler Layer
    Scheduler[Scheduler<br>Task Scheduling]

    %% External Systems
    Backend[Django Backend<br>API + SSR]:::external
    Websites[Monitored Websites<br>External Systems]:::external

    %% Connections - Infrastructure
    RabbitMQ -->|Tasks| Celery
    RabbitMQ -->|Tasks| Lighthouse
    
    %% Connections - Workers
    Celery -->|Results| Backend
    Lighthouse -->|Performance Data| Backend
    Lighthouse -->|Analyzes| Websites
    Heartbeats -->|Health Status| Backend
    
    %% Connections - Monitoring
    Prometheus -->|Alerts| Alertmanager
    Prometheus -.->|Scrapes Metrics| RabbitMQ
    Prometheus -.->|Scrapes Metrics| Blackbox
    Blackbox -.->|Probes| Websites
    Backend -->|PromQL| Prometheus
    Alertmanager -->|Webhooks| Backend
    
    %% Connections - Scheduler
    Scheduler -->|Schedules Tasks| RabbitMQ
    
    %% Apply styles
    RabbitMQ:::infrastructure
    
    Celery:::worker
    Lighthouse:::worker
    Heartbeats:::worker
    
    Prometheus:::monitoring
    Alertmanager:::monitoring
    Blackbox:::monitoring
    
    Scheduler:::scheduler
```

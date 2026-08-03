# Loading Overlay Component

A reusable loading overlay component that displays progress for multiple tasks with real-time status updates.

## Usage

Include the component in your template:

```django
{% include "components/loading_overlay.html" with project_id=project.id title="Scanning your website..." description="We're analyzing your website to gather performance data" tasks="favicon,sitemap,prometheus,scraping,lighthouse" %}
```

> Django template tags cannot span multiple lines — keep the `{% include %}` on a single line.

## Parameters

- `project_id`: The project ID for API calls (required)
- `title`: Main title for the loading overlay (optional, defaults to "Loading...")
- `description`: Description text below the title (optional, defaults to "Please wait while we process your request")
- `tasks`: Comma-separated list of task names to monitor (required)

## Features

- **Real-time progress updates**: Automatically polls the API every 2 seconds
- **Visual progress bars**: Shows progress for each task with different states
- **Status indicators**: Displays current status (Waiting, Processing, Completed, Failed)
- **Responsive design**: Works on all screen sizes
- **Completion handling**: Shows completion message and auto-reloads page when done

## Task States

- **Waiting**: Gray progress bar, "⏳ Waiting..." status
- **Processing**: Blue progress bar with animation, shows progress if available
- **Completed**: Green progress bar, "✓ Completed" status
- **Failed**: Red progress bar, "✗ Failed" status
- **Unknown**: Gray progress bar, "❓ Unknown" status
- **Deploying**: Purple progress bar with animation, "🚀 Deploying..." status

## API Requirements

The component expects an API endpoint at `/api/project/{project_id}/task_status/` that returns:

```json
{
  "favicon_status": "SUCCESS|PENDING|FAILURE|UNKNOWN",
  "sitemap_status": "SUCCESS|PENDING|FAILURE|UNKNOWN",
  "prometheus_status": "SUCCESS|PENDING|FAILURE|UNKNOWN|DEPLOYING",
  "scraping_status": "SUCCESS|PENDING|FAILURE|UNKNOWN",
  "scraping_progress": {"completed": 5, "total": 10},
  "lighthouse_status": "SUCCESS|PENDING|FAILURE|UNKNOWN",
  "lighthouse_progress": {"completed": 3, "total": 8},
  "reports_status": "SUCCESS|PENDING|FAILURE|UNKNOWN",
  "reports_progress": {"completed": 1, "total": 1},
  "all_complete": true
}
```

## Example Implementation

```django
{% extends "application.html" %}
{% load static %}

{% block content %}
  <div class="container mx-auto px-4">
    <h1>Project Dashboard</h1>
    
    <!-- Include the loading overlay -->
    {% include "components/loading_overlay.html" with project_id=project.id title="Processing your project..." description="We're setting up monitoring for your website" tasks="favicon,sitemap,prometheus,scraping,lighthouse,reports" %}
    
    <!-- Your other content here -->
    <div class="mt-8">
      <!-- Project content -->
    </div>
  </div>
{% endblock %}
```

## Customization

You can customize the appearance by modifying the CSS classes in the component template. The component uses Tailwind CSS classes for styling. 
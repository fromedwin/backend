from django.db import migrations, models

import favicons.models


class Migration(migrations.Migration):

    dependencies = [
        ('favicons', '0003_favicon_celery_task_log'),
    ]

    operations = [
        migrations.AlterField(
            model_name='favicon',
            name='favicon',
            field=models.FileField(
                blank=True,
                help_text="Application's favicon",
                null=True,
                upload_to=favicons.models.favicon_upload_path,
            ),
        ),
    ]

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("stocks", "0002_pushsubscription_stockalert"),
    ]

    operations = [
        migrations.AddField(
            model_name="stockalert",
            name="last_notified_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="stockalert",
            name="rearm_ready",
            field=models.BooleanField(default=True),
        ),
    ]

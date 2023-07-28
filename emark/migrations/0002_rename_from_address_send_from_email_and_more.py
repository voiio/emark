import json

from django.db import migrations, models


def forwards_func(apps, schema_editor):  # pragma: no cover
    Send = apps.get_model("emark", "Send")
    for send in Send.objects.all():
        send.to = json.dumps([send.to])
        send.save(update_fields=["to"])


class Migration(migrations.Migration):
    dependencies = [
        ("emark", "0001_initial"),
    ]

    operations = [
        migrations.RenameField(
            model_name="send",
            old_name="from_address",
            new_name="from_email",
        ),
        migrations.RenameField(
            model_name="send",
            old_name="to_address",
            new_name="to",
        ),
        migrations.RunPython(
            forwards_func,
        ),
        migrations.AlterField(
            model_name="send",
            name="to",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="send",
            name="cc",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="send",
            name="bcc",
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name="send",
            name="reply_to",
            field=models.JSONField(default=list),
        ),
        migrations.AlterField(
            model_name="send",
            name="from_email",
            field=models.TextField(max_length=998),
        ),
    ]

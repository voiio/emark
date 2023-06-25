# Generated by Django 4.2.2 on 2023-06-25 09:50

import uuid

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Send",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("from_address", models.EmailField(max_length=254)),
                ("to_address", models.EmailField(max_length=254)),
                ("subject", models.TextField(max_length=998)),
                ("body", models.TextField()),
                ("html", models.TextField()),
                ("utm", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name="Open",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("headers", models.JSONField(default=dict)),
                ("ip_address", models.GenericIPAddressField()),
                ("utm", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "email",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="emark.send"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Click",
            fields=[
                (
                    "uuid",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                        unique=True,
                    ),
                ),
                ("headers", models.JSONField(default=dict)),
                ("ip_address", models.GenericIPAddressField()),
                ("utm", models.JSONField(default=dict)),
                ("redirect_url", models.URLField()),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                (
                    "email",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="emark.send"
                    ),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
    ]

from __future__ import annotations

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("core", "0001_default_site"),
        ("core", "0017_basemaps"),
    ]

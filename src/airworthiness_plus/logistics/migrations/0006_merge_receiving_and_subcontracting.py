"""Join the separately shipped Goods In and subcontracting migrations."""

from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [
        ("logistics", "0004_subcontractor_record_rules"),
        ("logistics", "0005_verified_receiving_and_stock"),
    ]
    operations = []

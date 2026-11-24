"""The owner of an aircraft is a customer record, not free text (REQ-208, REQ-209).

What was typed as Owned By is kept: it is the name of the customer made
for it, and it stays in every earlier entry of the aircraft's history.
The steps and their order are explained in ``aircraft/sql.py``.
"""

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.aircraft import sql as aircraft_sql
from airworthiness_plus.history import sql


class Migration(migrations.Migration):
    dependencies = [
        ("aircraft", "0002_aircraft_designation_aircraft_manufacturer"),
        ("customers", "0001_initial"),
        ("history", "0004_hash_algorithm"),
        ("organisations", "0006_approvals_held"),
    ]

    operations = [
        migrations.AddField(
            model_name="aircraft",
            name="customer",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.PROTECT,
                related_name="aircraft",
                to="customers.customer",
            ),
        ),
        migrations.RunSQL(
            aircraft_sql.OWNERS_TO_CUSTOMERS_BEGIN, aircraft_sql.OWNERS_TO_CUSTOMERS_END
        ),
        migrations.RunSQL(
            sql.for_each_organisation(aircraft_sql.CUSTOMER_FOR_EACH_OWNER),
            migrations.RunSQL.noop,
        ),
        migrations.RemoveField(model_name="aircraft", name="owner"),
        migrations.RunSQL(
            sql.for_each_organisation(aircraft_sql.AIRCRAFT_TAKE_THEIR_CUSTOMER),
            migrations.RunSQL.noop,
        ),
        migrations.RunSQL(
            aircraft_sql.OWNERS_TO_CUSTOMERS_END, aircraft_sql.OWNERS_TO_CUSTOMERS_BEGIN
        ),
        migrations.AlterField(
            model_name="aircraft",
            name="customer",
            field=models.ForeignKey(
                on_delete=django.db.models.deletion.PROTECT,
                related_name="aircraft",
                to="customers.customer",
            ),
        ),
        migrations.RunSQL(
            *sql.same_organisation("aircraft_aircraft", "customer_id", "customers_customer")
        ),
    ]

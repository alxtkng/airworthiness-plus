"""The owner of an aircraft is a customer record, not free text (REQ-208, REQ-209).

What was typed as Owned By is kept: it is the name of the customer made
for it, and it stays in every earlier entry of the aircraft's history.
The steps and their order are explained in ``aircraft/sql.py``.

This migration cannot be reversed, and says so before it changes anything.
Going back would need the text that was typed for each aircraft, and the
column that held it is removed: nothing here can say which words stood
there, and customers renamed or changed since would no longer agree with
them. The text itself is still in the earlier entries of each aircraft's
history.
"""

import django.db.models.deletion
from django.db import migrations, models

from airworthiness_plus.aircraft import sql as aircraft_sql
from airworthiness_plus.history import sql


class CannotBeReversed(migrations.RunPython):
    """An operation that does nothing forwards and refuses to go back, with the reason.

    Django asks every operation whether it can be reversed before it
    reverses any, so the migration is refused whole and not part way
    through (independent review of 24 November 2026, finding 13).
    """

    def __init__(self, reason: str) -> None:
        super().__init__(migrations.RunPython.noop)
        self.reason = reason

    def __repr__(self) -> str:
        return f"CannotBeReversed: {self.reason}"


class Migration(migrations.Migration):
    dependencies = [
        ("aircraft", "0002_aircraft_designation_aircraft_manufacturer"),
        ("customers", "0001_initial"),
        ("history", "0004_hash_algorithm"),
        ("organisations", "0006_approvals_held"),
    ]

    operations = [
        CannotBeReversed(
            "the text typed as Owned By was removed when it became customer records, "
            "and cannot be put back"
        ),
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

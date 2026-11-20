"""A point of a review is checked against the review read under a lock."""

from django.db import migrations

from airworthiness_plus.reviews import sql


class Migration(migrations.Migration):
    dependencies = [
        ("reviews", "0005_reviewstaff_recorded_on"),
    ]

    operations = [
        migrations.RunSQL(sql.REVIEW_ITEM_FIXED_LOCKED, sql.REVIEW_ITEM_FIXED_UNLOCKED),
    ]

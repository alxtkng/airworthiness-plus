"""Keep dependencies with unfinished modifications open for baseline signing."""

from django.db import migrations

from airworthiness_plus.configuration.sql import CREATE_RULES

FUNCTION = (
    CREATE_RULES[CREATE_RULES.index("CREATE FUNCTION configuration_baseline_before_insert") :]
    .split("CREATE TRIGGER baseline_keeps", 1)[0]
    .replace("CREATE FUNCTION", "CREATE OR REPLACE FUNCTION", 1)
)
INSTALL = FUNCTION.replace(
    "(needs_change AND change_id IS NULL)",
    """(needs_change AND NOT EXISTS (
                SELECT 1 FROM modifications_change
                 WHERE id = configuration_position.change_id AND embodied_on IS NOT NULL
           ))""",
)


class Migration(migrations.Migration):
    dependencies = [("configuration", "0001_initial")]
    operations = [migrations.RunSQL(INSTALL, FUNCTION)]

"""The parts of the Phase 1 sample that the top-up adds once (REQ-294)."""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("organisations", "0010_reweigh_threshold"),
        ("sample", "0001_initial"),
    ]

    operations = [
        migrations.RemoveConstraint(
            model_name="added",
            name="sample_part_is_known",
        ),
        migrations.AlterField(
            model_name="added",
            name="part",
            field=models.CharField(
                choices=[
                    ("People", "People"),
                    ("Defects", "Defects"),
                    ("Contracts", "Contracts"),
                    ("Components", "Components"),
                    ("Modifications and Weighings", "Modifications and Weighings"),
                    ("Departures and Annual Review", "Departures and Annual Review"),
                    ("Sources of Directives", "Sources of Directives"),
                    ("Transfer and Configuration", "Transfer and Configuration"),
                ],
                max_length=40,
                verbose_name="Part of the Sample",
            ),
        ),
        migrations.AddConstraint(
            model_name="added",
            constraint=models.CheckConstraint(
                condition=models.Q(
                    (
                        "part__in",
                        [
                            "People",
                            "Defects",
                            "Contracts",
                            "Components",
                            "Modifications and Weighings",
                            "Departures and Annual Review",
                            "Sources of Directives",
                            "Transfer and Configuration",
                        ],
                    )
                ),
                name="sample_part_is_known",
            ),
        ),
    ]

from django.db import migrations, models


def quarter_to_period(apps, schema_editor):
    """Convert existing quarterly labels ("Q3 2026") to season periods
    ("S2 2026") using the quarter's starting month: Q1,Q2 -> S1 (Jan/Apr),
    Q3 -> S2 (Jul), Q4 -> S3 (Oct)."""
    AgeProcessingLog = apps.get_model("players", "AgeProcessingLog")
    mapping = {"Q1": "S1", "Q2": "S1", "Q3": "S2", "Q4": "S3"}
    for log in AgeProcessingLog.objects.all():
        prefix = log.period[:2]
        if prefix in mapping:
            log.period = f"{mapping[prefix]}{log.period[2:]}"
            log.save(update_fields=["period"])


def period_to_quarter(apps, schema_editor):
    """Best-effort reverse (S1->Q1, S2->Q3, S3->Q4)."""
    AgeProcessingLog = apps.get_model("players", "AgeProcessingLog")
    mapping = {"S1": "Q1", "S2": "Q3", "S3": "Q4"}
    for log in AgeProcessingLog.objects.all():
        prefix = log.period[:2]
        if prefix in mapping:
            log.period = f"{mapping[prefix]}{log.period[2:]}"
            log.save(update_fields=["period"])


class Migration(migrations.Migration):

    dependencies = [
        ("players", "0002_ageprocessinglog"),
    ]

    operations = [
        migrations.RenameField(
            model_name="ageprocessinglog",
            old_name="quarter",
            new_name="period",
        ),
        migrations.RunPython(quarter_to_period, period_to_quarter),
    ]

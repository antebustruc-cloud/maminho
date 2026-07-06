"""
Data migration: rename the 'soccer_field' facility type to 'stadium'.
Additive/safe on production — only touches Facility rows that still
carry the old value. Reversible for a clean rollback.
"""

from django.db import migrations


def forwards(apps, schema_editor):
    Facility = apps.get_model("clubs", "Facility")
    Facility.objects.filter(facility_type="soccer_field").update(facility_type="stadium")


def backwards(apps, schema_editor):
    Facility = apps.get_model("clubs", "Facility")
    Facility.objects.filter(facility_type="stadium").update(facility_type="soccer_field")


class Migration(migrations.Migration):

    dependencies = [
        ("clubs", "0003_alter_facility_facility_type_alter_season_sport_and_more"),
    ]

    operations = [
        migrations.RunPython(forwards, backwards),
    ]

"""
Phase 3c data migration for the clubs app:
1. Currency: Club.kc_balance and ConstructionProject.cost_kc convert from
   KC to LC (x100). Reversible.
2. Seasons: quarterly names ("Q3 2026") become 3-per-year season names
   ("S2 2026"), recomputed from each season's start_date.
"""
import re

from django.db import migrations
from django.db.models import F

Q_NAME = re.compile(r"^Q[1-4] (\d{4})$")
S_NAME = re.compile(r"^S[1-3] (\d{4})$")


def forwards(apps, schema_editor):
    Club = apps.get_model("clubs", "Club")
    ConstructionProject = apps.get_model("clubs", "ConstructionProject")
    Season = apps.get_model("clubs", "Season")

    Club.objects.update(kc_balance=F("kc_balance") * 100)
    ConstructionProject.objects.update(cost_kc=F("cost_kc") * 100)

    for season in Season.objects.all():
        if Q_NAME.match(season.name):
            period = (season.start_date.month - 1) // 4 + 1
            season.name = f"S{period} {season.start_date.year}"
            season.save(update_fields=["name"])


def backwards(apps, schema_editor):
    Club = apps.get_model("clubs", "Club")
    ConstructionProject = apps.get_model("clubs", "ConstructionProject")
    Season = apps.get_model("clubs", "Season")

    Club.objects.update(kc_balance=F("kc_balance") / 100)
    ConstructionProject.objects.update(cost_kc=F("cost_kc") / 100)

    for season in Season.objects.all():
        if S_NAME.match(season.name):
            quarter = (season.start_date.month - 1) // 3 + 1
            season.name = f"Q{quarter} {season.start_date.year}"
            season.save(update_fields=["name"])


class Migration(migrations.Migration):
    dependencies = [
        ("clubs", "0006_constructionproject_construction_company_and_more"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]

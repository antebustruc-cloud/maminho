"""
Currency migration (Phase 3c) for the players app: manager balances,
bid wage offers, contract wages, club deal fees and signing bonuses all
convert from KC to LC (x100). Reversible.
"""
from django.db import migrations
from django.db.models import F


def forwards(apps, schema_editor):
    apps.get_model("players", "ManagerProfile").objects.update(kc_balance=F("kc_balance") * 100)
    apps.get_model("players", "Bid").objects.update(wage_offer=F("wage_offer") * 100)
    apps.get_model("players", "Contract").objects.update(wage=F("wage") * 100)
    apps.get_model("players", "ClubDeal").objects.update(
        monthly_fee=F("monthly_fee") * 100, signing_bonus=F("signing_bonus") * 100)


def backwards(apps, schema_editor):
    apps.get_model("players", "ManagerProfile").objects.update(kc_balance=F("kc_balance") / 100)
    apps.get_model("players", "Bid").objects.update(wage_offer=F("wage_offer") / 100)
    apps.get_model("players", "Contract").objects.update(wage=F("wage") / 100)
    apps.get_model("players", "ClubDeal").objects.update(
        monthly_fee=F("monthly_fee") / 100, signing_bonus=F("signing_bonus") / 100)


class Migration(migrations.Migration):
    dependencies = [
        ("players", "0004_alter_managerprofile_kc_balance"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]

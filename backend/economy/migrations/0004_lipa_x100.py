"""
Currency migration (Phase 3c): 1 KC = 100 LipaCoin (LC). All stored
amounts convert from KC to LC by multiplying by 100. Reversible (//100).
"""
from django.db import migrations
from django.db.models import F


def forwards(apps, schema_editor):
    Transaction = apps.get_model("economy", "Transaction")
    Transaction.objects.update(amount=F("amount") * 100)


def backwards(apps, schema_editor):
    Transaction = apps.get_model("economy", "Transaction")
    Transaction.objects.update(amount=F("amount") / 100)


class Migration(migrations.Migration):
    dependencies = [
        ("economy", "0003_transaction_from_company_transaction_to_company_and_more"),
    ]
    operations = [migrations.RunPython(forwards, backwards)]

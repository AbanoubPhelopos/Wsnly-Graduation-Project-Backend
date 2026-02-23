from django.db import migrations


def backfill_has_result(apps, schema_editor):
    RouteHistory = apps.get_model("history", "RouteHistory")
    RouteHistory.objects.filter(status="success", has_result=False).update(
        has_result=True
    )


def noop_reverse(apps, schema_editor):
    return


class Migration(migrations.Migration):
    dependencies = [
        ("history", "0002_routehistory_preference_and_selection_fields"),
    ]

    operations = [
        migrations.RunPython(backfill_has_result, noop_reverse),
    ]

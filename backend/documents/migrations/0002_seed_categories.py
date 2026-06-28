from django.db import migrations


DEFAULT_CATEGORIES = [
    "Offer Letters",
    "Appointment Letters",
    "HR Documents",
]


def seed_categories(apps, schema_editor):
    DocumentCategory = apps.get_model('documents', 'DocumentCategory')
    for name in DEFAULT_CATEGORIES:
        DocumentCategory.objects.get_or_create(name=name)


def unseed_categories(apps, schema_editor):
    DocumentCategory = apps.get_model('documents', 'DocumentCategory')
    DocumentCategory.objects.filter(name__in=DEFAULT_CATEGORIES).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('documents', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(seed_categories, unseed_categories),
    ]

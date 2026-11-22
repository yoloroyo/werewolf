from django.db import migrations


CATEGORIES = [
    ('Мотоциклы', 'motocikly'),
    ('Экипировка', 'ekipirovka'),
    ('Масла / химия', 'masla'),
    ('Шины', 'shiny'),
    ('Запчасти', 'zapchasti'),
    ('Аксессуары', 'aksessuary'),
]


def seed(apps, schema_editor):
    ProductCategory = apps.get_model('shop', 'ProductCategory')
    for name, slug in CATEGORIES:
        ProductCategory.objects.get_or_create(slug=slug, defaults={'name': name})


def unseed(apps, schema_editor):
    ProductCategory = apps.get_model('shop', 'ProductCategory')
    ProductCategory.objects.filter(slug__in=[s for _, s in CATEGORIES]).delete()


class Migration(migrations.Migration):
    dependencies = [('shop', '0001_initial')]
    operations = [migrations.RunPython(seed, unseed)]

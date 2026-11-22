#!/usr/bin/env python3
"""
Загружает данные из seed_data/ в БД. Запуск из корня проекта:
    python scripts/seed.py
Повторный запуск безопасен: уже существующие записи обновляются, не дублируются.
"""
import json
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
SEED_DIR = BASE_DIR / 'seed_data'
IMAGES_DIR = SEED_DIR / 'images'

sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'motoshop.settings')

import django
django.setup()

from django.core.files import File
from shop.models import (Brand, MotoCategory, Motorcycle,
                         ProductCategory, Product, ProductImage,
                         Equipment, EquipmentType,
                         Oil, Tire,
                         Part, PartType,
                         Accessory, AccessoryType,
                         Partner, Review)


def load_json(name):
    path = SEED_DIR / name
    if not path.exists():
        print(f'  [skip] {name} не найден')
        return []
    with path.open(encoding='utf-8') as f:
        return json.load(f)


def attach_image(obj, field, folder, filename):
    if not filename:
        return False
    path = IMAGES_DIR / folder / filename
    if not path.exists():
        print(f'    картинка не найдена: {path}')
        return False
    with path.open('rb') as f:
        getattr(obj, field).save(filename, File(f), save=True)
    return True


def attach_gallery(product, folder, filenames):
    for name in filenames or []:
        path = IMAGES_DIR / folder / name
        if not path.exists():
            print(f'    картинка галереи не найдена: {path}')
            continue
        if ProductImage.objects.filter(product=product, image__endswith=name).exists():
            continue
        img = ProductImage(product=product)
        with path.open('rb') as f:
            img.image.save(name, File(f), save=True)


def seed_brands():
    print('Бренды:')
    for data in load_json('brands.json'):
        obj, created = Brand.objects.get_or_create(name=data['name'])
        attach_image(obj, 'logo', 'brands', data.get('logo', ''))
        print(f'  {"+" if created else "~"} {obj.name}')


def seed_moto_categories():
    print('Категории мотоциклов:')
    for data in load_json('moto_categories.json'):
        obj, created = MotoCategory.objects.get_or_create(
            name=data['name'], defaults={'slug': data.get('slug', '')})
        print(f'  {"+" if created else "~"} {obj.name}')


def _seed_type(model, label, filename):
    print(f'{label}:')
    for data in load_json(filename):
        obj, created = model.objects.get_or_create(
            name=data['name'], defaults={'slug': data.get('slug', '')})
        print(f'  {"+" if created else "~"} {obj.name}')


def seed_equipment_types():
    _seed_type(EquipmentType, 'Типы экипировки', 'equipment_types.json')


def seed_part_types():
    _seed_type(PartType, 'Типы запчастей', 'part_types.json')


def seed_accessory_types():
    _seed_type(AccessoryType, 'Типы аксессуаров', 'accessory_types.json')


def _get_pc(slug):
    return ProductCategory.objects.filter(slug=slug).first()


def seed_motorcycles():
    print('Мотоциклы:')
    cat = _get_pc('motocikly')
    if not cat:
        print('  [skip] категория motocikly не найдена')
        return
    for data in load_json('motorcycles.json'):
        brand = Brand.objects.filter(name=data['brand']).first()
        moto_cat = MotoCategory.objects.filter(name=data['moto_category']).first()
        if not brand or not moto_cat:
            print(f'  [skip] {data.get("name")}: нет бренда/категории мото')
            continue
        obj, created = Motorcycle.objects.get_or_create(
            brand=brand, name=data['name'], year=data['year'],
            defaults={
                'category': cat,
                'moto_category': moto_cat,
                'engine_cc': data['engine_cc'],
                'power_hp': data.get('power_hp'),
                'weight_kg': data.get('weight_kg'),
                'color': data.get('color', ''),
                'price': data['price'],
                'stock': data.get('stock', 1),
                'short_description': data.get('short_description', ''),
                'description': data.get('description', ''),
            })
        if not created:
            obj.price = data['price']
            obj.stock = data.get('stock', obj.stock)
            obj.save()

        images = []
        if data.get('image'):
            images.append(data['image'])
        images.extend(data.get('gallery', []))
        attach_gallery(obj, 'motorcycles', images)
        print(f'  {"+" if created else "~"} {obj}')


def _seed_subclass(filename, model, category_slug, folder,
                   type_model=None, type_field=None, type_json_key=None,
                   extra_fields=None):
    print(f'{model._meta.verbose_name_plural}:')
    cat = _get_pc(category_slug)
    if not cat:
        print(f'  [skip] категория {category_slug} не найдена')
        return
    for data in load_json(filename):
        brand = Brand.objects.filter(name=data['brand']).first() if data.get('brand') else None
        kwargs = {
            'category': cat,
            'brand': brand,
            'price': data['price'],
            'stock': data.get('stock', 1),
            'short_description': data.get('short_description', ''),
            'description': data.get('description', ''),
        }
        if type_model and type_field and type_json_key:
            type_obj = type_model.objects.filter(name=data[type_json_key]).first()
            if not type_obj:
                print(f'  [skip] {data["name"]}: тип "{data[type_json_key]}" не найден')
                continue
            kwargs[type_field] = type_obj
        for f in (extra_fields or []):
            if f in data:
                kwargs[f] = data[f]
        obj, created = model.objects.get_or_create(name=data['name'], defaults=kwargs)
        if not created:
            for k, v in kwargs.items():
                setattr(obj, k, v)
            obj.save()
        if data.get('image'):
            attach_gallery(obj, folder, [data['image']])
        print(f'  {"+" if created else "~"} {obj}')


def seed_equipment():
    _seed_subclass('equipment.json', Equipment, 'ekipirovka', 'equipment',
                   type_model=EquipmentType, type_field='equipment_type', type_json_key='equipment_type',
                   extra_fields=['size', 'color'])


def seed_oils():
    _seed_subclass('oils.json', Oil, 'masla', 'oils',
                   extra_fields=['viscosity', 'volume_ml'])


def seed_tires():
    _seed_subclass('tires.json', Tire, 'shiny', 'tires',
                   extra_fields=['diameter'])


def seed_parts():
    _seed_subclass('parts.json', Part, 'zapchasti', 'parts',
                   type_model=PartType, type_field='part_type', type_json_key='part_type')


def seed_accessories():
    _seed_subclass('accessories.json', Accessory, 'aksessuary', 'accessories',
                   type_model=AccessoryType, type_field='accessory_type', type_json_key='accessory_type')


def seed_partners():
    print('Партнёры:')
    for data in load_json('partners.json'):
        obj, created = Partner.objects.get_or_create(name=data['name'])
        attach_image(obj, 'logo', 'partners', data.get('logo', ''))
        print(f'  {"+" if created else "~"} {obj.name}')


def seed_reviews():
    print('Отзывы:')
    for data in load_json('reviews.json'):
        obj, created = Review.objects.get_or_create(
            author_name=data['author_name'], text=data['text'],
            defaults={'rating': data.get('rating', 5)})
        print(f'  {"+" if created else "~"} {obj}')


def main():
    seed_brands()
    seed_moto_categories()
    seed_equipment_types()
    seed_part_types()
    seed_accessory_types()
    seed_motorcycles()
    seed_equipment()
    seed_oils()
    seed_tires()
    seed_parts()
    seed_accessories()
    seed_partners()
    seed_reviews()
    print('\nГотово')


if __name__ == '__main__':
    main()

from django.db import models
from django.urls import reverse
from django.utils.text import slugify
from django.conf import settings
from decimal import Decimal


class Brand(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)
    logo = models.ImageField('Логотип', upload_to='brands/', blank=True, null=True)

    class Meta:
        verbose_name = 'Бренд'
        verbose_name_plural = 'Бренды'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False) or 'brand'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class MotoCategory(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = 'Категория мотоцикла'
        verbose_name_plural = 'Категории мотоциклов'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False) or 'moto-category'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Order(models.Model):
    STATUS_CHOICES = [
        ('new', 'Новый'),
        ('processing', 'В обработке'),
        ('shipped', 'Отправлен'),
        ('completed', 'Завершён'),
        ('cancelled', 'Отменён'),
    ]
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
                             null=True, blank=True, related_name='orders',
                             verbose_name='Пользователь')
    full_name = models.CharField('Имя и фамилия', max_length=150)
    phone = models.CharField('Телефон', max_length=30)
    email = models.EmailField('Email', blank=True)
    address = models.CharField('Адрес доставки', max_length=255)
    comment = models.TextField('Комментарий', blank=True)
    status = models.CharField('Статус', max_length=20, choices=STATUS_CHOICES, default='new')
    total = models.DecimalField('Сумма заказа', max_digits=12, decimal_places=2, default=Decimal('0'))
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Заказ'
        verbose_name_plural = 'Заказы'
        ordering = ['-created_at']

    def __str__(self):
        return f'Заказ #{self.pk} - {self.full_name}'

    def recalc_total(self):
        self.total = sum((item.subtotal for item in self.items.all()), Decimal('0'))
        self.save(update_fields=['total'])


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE,
                              related_name='items', verbose_name='Заказ')
    product = models.ForeignKey('Product', on_delete=models.SET_NULL,
                                null=True, blank=True, verbose_name='Товар')
    name_snapshot = models.CharField('Название (снимок)', max_length=255, blank=True)
    price = models.DecimalField('Цена на момент заказа', max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField('Количество', default=1)

    class Meta:
        verbose_name = 'Позиция заказа'
        verbose_name_plural = 'Позиции заказа'

    def __str__(self):
        return f'{self.display_name} × {self.quantity}'

    @property
    def display_name(self):
        return self.name_snapshot or str(self.product or 'Товар')

    @property
    def subtotal(self):
        return self.price * self.quantity


class Review(models.Model):
    RATING_CHOICES = [(i, '★' * i) for i in range(1, 6)]
    author_name = models.CharField('Имя', max_length=100)
    rating = models.PositiveSmallIntegerField('Оценка', choices=RATING_CHOICES, default=5)
    text = models.TextField('Отзыв')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Отзыв'
        verbose_name_plural = 'Отзывы'
        ordering = ['-created_at']

    def __str__(self):
        return f'{self.author_name} ({self.rating}★)'


class ProductCategory(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = 'Категория товаров'
        verbose_name_plural = 'Категории товаров'
        ordering = ['pk']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False) or 'cat'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Product(models.Model):
    category = models.ForeignKey(ProductCategory, on_delete=models.PROTECT,
                                 related_name='products', verbose_name='Категория')
    brand = models.ForeignKey(Brand, on_delete=models.SET_NULL, null=True, blank=True,
                              related_name='products', verbose_name='Бренд')
    name = models.CharField('Название', max_length=200)
    slug = models.SlugField('Slug', max_length=220, unique=True, blank=True)
    price = models.DecimalField('Цена', max_digits=10, decimal_places=2)
    stock = models.PositiveIntegerField('В наличии', default=0)
    short_description = models.CharField('Краткое описание', max_length=255, blank=True)
    description = models.TextField('Описание', blank=True)
    is_active = models.BooleanField('Опубликован', default=True)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Товар'
        verbose_name_plural = 'Товары'
        ordering = ['-created_at']

    def save(self, *args, **kwargs):
        if not self.slug:
            base = self.name
            if self.brand:
                base = f'{self.brand.name}-{base}'
            self.slug = slugify(base, allow_unicode=False)[:220] or 'product'
        super().save(*args, **kwargs)

    def __str__(self):
        if self.brand_id:
            return f'{self.brand.name} {self.name}'
        return self.name

    def get_absolute_url(self):
        return reverse('shop:product_detail', args=[self.slug])

    @property
    def in_stock(self):
        return self.stock > 0

    @property
    def main_image(self):
        first = self.images.first()
        return first.image if first else None


class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='images', verbose_name='Товар')
    image = models.ImageField('Фото', upload_to='products/gallery/')
    caption = models.CharField('Подпись', max_length=150, blank=True)

    class Meta:
        verbose_name = 'Фотография товара'
        verbose_name_plural = 'Фотографии товаров'

    def __str__(self):
        return f'Фото #{self.pk} - {self.product}'


class Profile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='profile', verbose_name='Пользователь')
    full_name = models.CharField('Имя и фамилия', max_length=150, blank=True)
    phone = models.CharField('Телефон', max_length=30, blank=True)
    address = models.CharField('Адрес', max_length=255, blank=True)

    class Meta:
        verbose_name = 'Профиль'
        verbose_name_plural = 'Профили'

    def __str__(self):
        return f'Профиль {self.user}'


class EmailConfirmation(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE,
                                related_name='email_confirmation')
    code = models.CharField('Код', max_length=6)
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Код подтверждения'
        verbose_name_plural = 'Коды подтверждения'

    def __str__(self):
        return f'Код для {self.user.email}'


class EquipmentType(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = 'Тип экипировки'
        verbose_name_plural = 'Типы экипировки'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False) or 'type'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Equipment(Product):
    equipment_type = models.ForeignKey(EquipmentType, on_delete=models.PROTECT,
                                       related_name='items', verbose_name='Тип')
    size = models.CharField('Размер', max_length=20, blank=True)
    color = models.CharField('Цвет', max_length=40, blank=True)

    class Meta:
        verbose_name = 'Экипировка'
        verbose_name_plural = 'Экипировка'


class Oil(Product):
    viscosity = models.CharField('Вязкость', max_length=20, blank=True,
                                 help_text='например 10W-40')
    volume_ml = models.PositiveIntegerField('Объём, мл', null=True, blank=True)

    class Meta:
        verbose_name = 'Масло / химия'
        verbose_name_plural = 'Масла / химия'


class Tire(Product):
    diameter = models.PositiveSmallIntegerField('Диаметр, дюйм', null=True, blank=True,
                                                help_text='например 17')

    class Meta:
        verbose_name = 'Шина'
        verbose_name_plural = 'Шины'


class PartType(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = 'Тип запчасти'
        verbose_name_plural = 'Типы запчастей'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False) or 'part-type'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Part(Product):
    part_type = models.ForeignKey(PartType, on_delete=models.PROTECT,
                                  related_name='items', verbose_name='Тип')

    class Meta:
        verbose_name = 'Запчасть'
        verbose_name_plural = 'Запчасти'


class Motorcycle(Product):
    moto_category = models.ForeignKey(MotoCategory, on_delete=models.PROTECT,
                                      related_name='motorcycles', verbose_name='Категория мотоцикла')
    year = models.PositiveIntegerField('Год выпуска')
    engine_cc = models.PositiveIntegerField('Объём двигателя, см³')
    power_hp = models.PositiveIntegerField('Мощность, л.с.', blank=True, null=True)
    weight_kg = models.PositiveIntegerField('Масса, кг', blank=True, null=True)
    color = models.CharField('Цвет', max_length=60, blank=True)

    class Meta:
        verbose_name = 'Мотоцикл'
        verbose_name_plural = 'Мотоциклы'


class AccessoryType(models.Model):
    name = models.CharField('Название', max_length=100, unique=True)
    slug = models.SlugField('Slug', max_length=120, unique=True, blank=True)

    class Meta:
        verbose_name = 'Тип аксессуара'
        verbose_name_plural = 'Типы аксессуаров'
        ordering = ['name']

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = slugify(self.name, allow_unicode=False) or 'accessory-type'
        super().save(*args, **kwargs)

    def __str__(self):
        return self.name


class Accessory(Product):
    accessory_type = models.ForeignKey(AccessoryType, on_delete=models.PROTECT,
                                       related_name='items', verbose_name='Тип')

    class Meta:
        verbose_name = 'Аксессуар'
        verbose_name_plural = 'Аксессуары'


class CheckoutReservation(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE,
                                related_name='reservations', verbose_name='Товар')
    quantity = models.PositiveIntegerField('Количество')
    session_key = models.CharField('Сессия', max_length=40)
    expires_at = models.DateTimeField('Истекает')
    created_at = models.DateTimeField('Создан', auto_now_add=True)

    class Meta:
        verbose_name = 'Резерв оформления'
        verbose_name_plural = 'Резервы оформления'

    def __str__(self):
        return f'{self.product} × {self.quantity} до {self.expires_at:%H:%M:%S}'


class Partner(models.Model):
    name = models.CharField('Название', max_length=100)
    logo = models.ImageField('Логотип', upload_to='partners/')

    class Meta:
        verbose_name = 'Партнёр'
        verbose_name_plural = 'Партнёры (нам доверяют)'
        ordering = ['pk']

    def __str__(self):
        return self.name

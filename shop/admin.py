from django.contrib import admin
from django.utils.html import format_html
from .models import (Brand, MotoCategory, Motorcycle, Order, OrderItem, Review,
                     ProductCategory, Product, ProductImage, Profile,
                     Equipment, Oil, Tire, EquipmentType, Part, PartType,
                     Accessory, AccessoryType, Partner, CheckoutReservation)


@admin.register(Brand)
class BrandAdmin(admin.ModelAdmin):
    list_display = ('name', 'logo_preview')
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}

    def logo_preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height:30px;" />', obj.logo.url)
        return '-'
    logo_preview.short_description = 'Логотип'


@admin.register(MotoCategory)
class MotoCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


@admin.register(ProductCategory)
class ProductCategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)
    prepopulated_fields = {'slug': ('name',)}


class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 3
    fields = ('image', 'preview', 'caption')
    readonly_fields = ('preview',)

    def preview(self, obj):
        if obj.pk and obj.image:
            return format_html('<img src="{}" style="height:80px;" />', obj.image.url)
        return '-'
    preview.short_description = 'Превью'


class ProductAdminMixin:
    list_filter = ('category', 'brand', 'is_active')
    search_fields = ('name', 'description')
    list_editable = ('price', 'stock', 'is_active')
    prepopulated_fields = {'slug': ('name',)}
    inlines = [ProductImageInline]

    def thumb(self, obj):
        if obj.main_image:
            return format_html('<img src="{}" style="height:50px;border-radius:4px;" />', obj.main_image.url)
        return '-'
    thumb.short_description = 'Фото'


@admin.register(Product)
class ProductAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'category', 'brand', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')


@admin.register(Motorcycle)
class MotorcycleAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'brand', 'moto_category', 'year', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')
    list_filter = ('brand', 'moto_category', 'is_active', 'year')
    search_fields = ('name', 'brand__name', 'description')
    fieldsets = (
        ('Основное', {
            'fields': ('category', 'brand', 'moto_category', 'name', 'slug', 'is_active'),
        }),
        ('Характеристики', {
            'fields': ('year', 'engine_cc', 'power_hp', 'weight_kg', 'color'),
        }),
        ('Продажа', {
            'fields': ('price', 'stock'),
        }),
        ('Описание', {
            'fields': ('short_description', 'description'),
        }),
    )


admin.site.register(EquipmentType)


@admin.register(Equipment)
class EquipmentAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'equipment_type', 'size', 'color', 'brand', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')
    list_filter = ('equipment_type', 'brand', 'is_active')


@admin.register(Oil)
class OilAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'viscosity', 'volume_ml', 'brand', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')


@admin.register(Tire)
class TireAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'diameter', 'brand', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')


admin.site.register(PartType)


@admin.register(Part)
class PartAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'part_type', 'brand', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')
    list_filter = ('part_type', 'brand', 'is_active')


admin.site.register(AccessoryType)


@admin.register(Accessory)
class AccessoryAdmin(ProductAdminMixin, admin.ModelAdmin):
    list_display = ('thumb', 'name', 'accessory_type', 'brand', 'price', 'stock', 'is_active')
    list_display_links = ('thumb', 'name')
    list_filter = ('accessory_type', 'brand', 'is_active')


class OrderItemInline(admin.TabularInline):
    model = OrderItem
    extra = 0
    readonly_fields = ('product', 'name_snapshot', 'price', 'quantity', 'subtotal')
    can_delete = False

    def subtotal(self, obj):
        return obj.subtotal if obj.pk else '-'
    subtotal.short_description = 'Сумма'


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ('id', 'full_name', 'phone', 'status', 'total', 'created_at')
    list_filter = ('status', 'created_at')
    search_fields = ('full_name', 'phone', 'email')
    list_editable = ('status',)
    readonly_fields = ('total', 'created_at')
    inlines = [OrderItemInline]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ('author_name', 'rating', 'short_text', 'created_at')
    list_filter = ('rating', 'created_at')
    search_fields = ('author_name', 'text')
    readonly_fields = ('created_at',)

    def short_text(self, obj):
        return obj.text[:80] + ('...' if len(obj.text) > 80 else '')
    short_text.short_description = 'Текст'


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'full_name', 'phone')
    search_fields = ('user__email', 'user__username', 'full_name', 'phone')


@admin.register(Partner)
class PartnerAdmin(admin.ModelAdmin):
    list_display = ('name', 'preview')
    search_fields = ('name',)

    def preview(self, obj):
        if obj.logo:
            return format_html('<img src="{}" style="height:40px;" />', obj.logo.url)
        return '-'
    preview.short_description = 'Логотип'


@admin.register(CheckoutReservation)
class CheckoutReservationAdmin(admin.ModelAdmin):
    list_display = ('product', 'quantity', 'session_key', 'expires_at')
    readonly_fields = ('created_at',)


admin.site.site_header = 'Werewolf - админка'
admin.site.site_title = 'Werewolf'
admin.site.index_title = 'Управление магазином'

from .cart import Cart
from .models import ProductCategory


def cart_count(request):
    return {'cart_count': len(Cart(request))}


def product_categories(request):
    return {'product_categories': ProductCategory.objects.all()}

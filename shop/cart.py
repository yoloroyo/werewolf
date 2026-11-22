from decimal import Decimal
from .models import Product

CART_KEY = 'cart'


class Cart:
    def __init__(self, request):
        self.session = request.session
        cart = self.session.get(CART_KEY)
        if not cart:
            cart = self.session[CART_KEY] = {}
        self.cart = cart

    def _save(self):
        self.session[CART_KEY] = self.cart
        self.session.modified = True

    def add(self, product, quantity=1):
        key = str(product.pk)
        if key in self.cart:
            self.cart[key]['quantity'] += quantity
        else:
            self.cart[key] = {
                'pk': product.pk,
                'quantity': quantity,
                'price': str(product.price),
            }
        self._save()

    def set_quantity(self, pk, quantity):
        key = str(pk)
        if key in self.cart:
            if quantity <= 0:
                del self.cart[key]
            else:
                self.cart[key]['quantity'] = quantity
            self._save()

    def remove(self, pk):
        key = str(pk)
        if key in self.cart:
            del self.cart[key]
            self._save()

    def clear(self):
        self.session[CART_KEY] = {}
        self.session.modified = True

    def __iter__(self):
        ids = [v['pk'] for v in self.cart.values()]
        products = {p.pk: p for p in Product.objects.filter(pk__in=ids).select_related('brand')}
        for item in self.cart.values():
            obj = products.get(item['pk'])
            if not obj:
                continue
            price = Decimal(item['price'])
            qty = item['quantity']
            yield {
                'pk': obj.pk,
                'object': obj,
                'quantity': qty,
                'price': price,
                'subtotal': price * qty,
            }

    def __len__(self):
        return sum(item['quantity'] for item in self.cart.values())

    @property
    def total(self):
        return sum((Decimal(i['price']) * i['quantity'] for i in self.cart.values()), Decimal('0'))

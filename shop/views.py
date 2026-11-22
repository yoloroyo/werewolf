import random
from datetime import timedelta
from django.shortcuts import render, get_object_or_404, redirect
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Q, F, Sum, Avg
from django.utils import timezone

from .models import (Brand, MotoCategory, Motorcycle, OrderItem, Review,
                     Product, ProductCategory, Profile, EmailConfirmation, Order,
                     Equipment, Oil, Tire, EquipmentType, Part, PartType,
                     Accessory, AccessoryType, Partner, CheckoutReservation)


RESERVATION_MINUTES = 30


def _available(product, exclude_session=None):
    qs = CheckoutReservation.objects.filter(
        product=product, expires_at__gt=timezone.now())
    if exclude_session:
        qs = qs.exclude(session_key=exclude_session)
    reserved = qs.aggregate(total=Sum('quantity'))['total'] or 0
    return max(product.stock - reserved, 0)
from .cart import Cart
from .forms import (OrderForm, ReviewForm, RegisterForm, LoginForm,
                    ConfirmForm, ProfileForm)


MOTO_CATEGORY_SLUG = 'motocikly'

SUBCLASS_BY_CATEGORY = {
    'motocikly': Motorcycle,
    'ekipirovka': Equipment,
    'masla': Oil,
    'shiny': Tire,
    'zapchasti': Part,
    'aksessuary': Accessory,
}


def home(request):
    first = ProductCategory.objects.first()
    if first:
        return redirect('shop:products', category_slug=first.slug)
    return render(request, 'shop/home.html')


def about(request):
    sold = OrderItem.objects.aggregate(total=Sum('quantity'))['total'] or 0
    avg = Review.objects.aggregate(avg=Avg('rating'))['avg']
    return render(request, 'shop/about.html', {
        'sold_count': sold,
        'brands_count': Brand.objects.count(),
        'avg_rating': round(avg, 1) if avg else 0,
        'reviews_count': Review.objects.count(),
        'partners': Partner.objects.all(),
    })


def reviews(request):
    if request.method == 'POST':
        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, 'Спасибо за отзыв!')
            return redirect('shop:reviews')
    else:
        form = ReviewForm()
    return render(request, 'shop/reviews.html', {
        'reviews': Review.objects.all(),
        'form': form,
    })


def _paginate(request, qs):
    paginator = Paginator(qs, 12)
    page = paginator.get_page(request.GET.get('page'))
    params = request.GET.copy()
    params.pop('page', None)
    return page, params.urlencode()


def products(request, category_slug):
    category = get_object_or_404(ProductCategory, slug=category_slug)
    model = SUBCLASS_BY_CATEGORY.get(category_slug, Product)
    qs = model.objects.filter(is_active=True, category=category).select_related('brand')

    brand_slug = request.GET.get('brand')
    query = request.GET.get('q', '').strip()
    sort = request.GET.get('sort', '-created_at')

    if brand_slug:
        qs = qs.filter(brand__slug=brand_slug)
    if query:
        qs = qs.filter(Q(name__icontains=query) | Q(brand__name__icontains=query)
                       | Q(description__icontains=query))

    extra_filters = {}
    if model is Motorcycle:
        moto_cat_slug = request.GET.get('moto_category')
        if moto_cat_slug:
            qs = qs.filter(moto_category__slug=moto_cat_slug)
        extra_filters = {
            'moto_categories': MotoCategory.objects.filter(motorcycles__is_active=True).distinct(),
            'selected_moto_category': moto_cat_slug or '',
        }
    elif model is Equipment:
        type_slug = request.GET.get('type')
        size = request.GET.get('size')
        color = request.GET.get('color')
        if type_slug:
            qs = qs.filter(equipment_type__slug=type_slug)
        if size:
            qs = qs.filter(size=size)
        if color:
            qs = qs.filter(color=color)
        extra_filters = {
            'equipment_types': EquipmentType.objects.filter(items__category=category).distinct(),
            'sizes': sorted(set(Equipment.objects.filter(category=category, is_active=True)
                                .exclude(size='').values_list('size', flat=True))),
            'colors': sorted(set(Equipment.objects.filter(category=category, is_active=True)
                                 .exclude(color='').values_list('color', flat=True))),
            'selected_type': type_slug or '',
            'selected_size': size or '',
            'selected_color': color or '',
        }
    elif model is Oil:
        viscosity = request.GET.get('viscosity')
        volume = request.GET.get('volume')
        if viscosity:
            qs = qs.filter(viscosity=viscosity)
        if volume:
            qs = qs.filter(volume_ml=volume)
        extra_filters = {
            'viscosities': sorted(set(Oil.objects.filter(category=category, is_active=True)
                                      .exclude(viscosity='').values_list('viscosity', flat=True))),
            'volumes': sorted(set(Oil.objects.filter(category=category, is_active=True,
                                                     volume_ml__isnull=False)
                                  .values_list('volume_ml', flat=True))),
            'selected_viscosity': viscosity or '',
            'selected_volume': volume or '',
        }
    elif model is Tire:
        diameter = request.GET.get('diameter')
        if diameter:
            qs = qs.filter(diameter=diameter)
        extra_filters = {
            'diameters': sorted(set(Tire.objects.filter(category=category, is_active=True,
                                                        diameter__isnull=False)
                                    .values_list('diameter', flat=True))),
            'selected_diameter': diameter or '',
        }
    elif model is Part:
        part_type_slug = request.GET.get('part_type')
        if part_type_slug:
            qs = qs.filter(part_type__slug=part_type_slug)
        extra_filters = {
            'part_types': PartType.objects.filter(items__category=category).distinct(),
            'selected_part_type': part_type_slug or '',
        }
    elif model is Accessory:
        accessory_type_slug = request.GET.get('accessory_type')
        if accessory_type_slug:
            qs = qs.filter(accessory_type__slug=accessory_type_slug)
        extra_filters = {
            'accessory_types': AccessoryType.objects.filter(items__category=category).distinct(),
            'selected_accessory_type': accessory_type_slug or '',
        }

    allowed_sort = {'price', '-price', '-created_at'}
    if model is Motorcycle:
        allowed_sort |= {'year', '-year'}
    if sort in allowed_sort:
        qs = qs.order_by(sort)

    page, querystring = _paginate(request, qs)

    brands = Brand.objects.filter(products__category=category, products__is_active=True).distinct()

    context = {
        'products': page,
        'page': page,
        'querystring': querystring,
        'category': category,
        'brands': brands,
        'selected_brand': brand_slug or '',
        'query': query,
        'sort': sort,
        'subclass': model.__name__.lower() if model is not Product else '',
    }
    context.update(extra_filters)
    return render(request, 'shop/products.html', context)


def product_detail(request, slug):
    product = get_object_or_404(
        Product.objects.select_related('brand', 'category').prefetch_related('images'),
        slug=slug, is_active=True)
    # If this is actually a Motorcycle, cast down to access extra fields
    try:
        product = product.motorcycle
    except Motorcycle.DoesNotExist:
        pass
    return render(request, 'shop/product_detail.html', {
        'product': product,
        'is_motorcycle': isinstance(product, Motorcycle),
    })


@require_POST
def cart_add(request, pk):
    item = get_object_or_404(Product, pk=pk, is_active=True)
    cart = Cart(request)
    current = cart.cart.get(str(pk), {}).get('quantity', 0)
    if not request.session.session_key:
        request.session.save()
    available = _available(item, exclude_session=request.session.session_key)
    if current + 1 > available:
        if request.headers.get('HX-Request'):
            return render(request, 'shop/_cart_badge.html', {'cart_count': len(cart)})
        messages.warning(request, f'Больше «{item}» на складе нет (доступно {available} шт.)')
        return redirect(request.META.get('HTTP_REFERER', 'shop:home'))
    cart.add(item, quantity=1)
    if request.headers.get('HX-Request'):
        return render(request, 'shop/_cart_badge.html', {'cart_count': len(cart)})
    messages.success(request, f'«{item}» добавлен в корзину')
    return redirect(request.META.get('HTTP_REFERER', 'shop:home'))


def cart_view(request):
    return render(request, 'shop/cart.html', {'cart': Cart(request)})


@require_POST
def cart_update(request, pk):
    try:
        qty = int(request.POST.get('quantity', 1))
    except ValueError:
        qty = 1
    item = Product.objects.filter(pk=pk, is_active=True).first()
    if item and qty > item.stock:
        qty = item.stock
        messages.warning(request, f'Доступно только {item.stock} шт. «{item}»')
    Cart(request).set_quantity(pk, qty)
    return redirect('shop:cart')


@require_POST
def cart_remove(request, pk):
    Cart(request).remove(pk)
    return redirect('shop:cart')


def checkout(request):
    cart = Cart(request)
    if len(cart) == 0:
        messages.warning(request, 'Корзина пуста')
        return redirect('shop:home')

    if not request.session.session_key:
        request.session.save()
    skey = request.session.session_key

    if request.method == 'POST':
        form = OrderForm(request.POST)
        if form.is_valid():
            with transaction.atomic():
                my_res = {r.product_id: r for r in CheckoutReservation.objects
                          .select_for_update()
                          .filter(session_key=skey, expires_at__gt=timezone.now())}
                for item in cart:
                    pk = item['object'].pk
                    if pk not in my_res or my_res[pk].quantity < item['quantity']:
                        messages.warning(request, 'Время брони истекло, попробуйте заново')
                        return redirect('shop:cart')

                order = form.save(commit=False)
                if request.user.is_authenticated:
                    order.user = request.user
                order.total = cart.total
                order.save()
                for item in cart:
                    obj = item['object']
                    OrderItem.objects.create(
                        order=order,
                        product=obj,
                        name_snapshot=str(obj),
                        price=item['price'],
                        quantity=item['quantity'],
                    )
                    Product.objects.filter(pk=obj.pk).update(stock=F('stock') - item['quantity'])
                CheckoutReservation.objects.filter(session_key=skey).delete()
            cart.clear()
            return render(request, 'shop/order_success.html', {'order': order})
    else:
        CheckoutReservation.objects.filter(session_key=skey).delete()
        expires_at = timezone.now() + timedelta(minutes=RESERVATION_MINUTES)
        with transaction.atomic():
            for item in cart:
                product = item['object']
                available = _available(product, exclude_session=skey)
                if item['quantity'] > available:
                    messages.warning(
                        request,
                        f'«{product}»: пока вы думали, товар разобрали. Осталось {available} шт.')
                    return redirect('shop:cart')
                CheckoutReservation.objects.create(
                    product=product, quantity=item['quantity'],
                    session_key=skey, expires_at=expires_at)

        initial = {}
        if request.user.is_authenticated and hasattr(request.user, 'profile'):
            p = request.user.profile
            initial = {'full_name': p.full_name, 'phone': p.phone, 'address': p.address,
                       'email': request.user.email}
        form = OrderForm(initial=initial)

    expires_at = (CheckoutReservation.objects.filter(session_key=skey)
                  .order_by('expires_at').values_list('expires_at', flat=True).first())
    return render(request, 'shop/checkout.html', {
        'form': form, 'cart': cart,
        'reservation_expires_ms': int(expires_at.timestamp() * 1000) if expires_at else 0,
    })


def register(request):
    if request.user.is_authenticated:
        return redirect('shop:profile')
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password1']
            user = User.objects.create_user(username=email, email=email, password=password)
            user.is_active = False
            user.save()
            Profile.objects.create(user=user)
            _send_confirmation(user, email)
            request.session['pending_email'] = email
            messages.info(request, f'Код отправлен на {email}. Введи его ниже.')
            return redirect('shop:confirm')
    else:
        form = RegisterForm()
    return render(request, 'shop/auth/register.html', {'form': form})


def confirm(request):
    email = request.session.get('pending_email')
    if not email:
        return redirect('shop:register')
    if request.method == 'POST':
        form = ConfirmForm(request.POST)
        if form.is_valid():
            try:
                user = User.objects.get(email=email)
                confirmation = user.email_confirmation
            except (User.DoesNotExist, EmailConfirmation.DoesNotExist):
                messages.error(request, 'Что-то пошло не так, зарегистрируйся заново')
                return redirect('shop:register')
            if form.cleaned_data['code'] == confirmation.code:
                user.is_active = True
                user.save()
                confirmation.delete()
                request.session.pop('pending_email', None)
                messages.success(request, 'Аккаунт активирован, войди')
                return redirect('shop:login')
            messages.error(request, 'Неверный код')
    else:
        form = ConfirmForm()
    return render(request, 'shop/auth/confirm.html', {'form': form, 'email': email})


def _send_confirmation(user, email):
    code = f'{random.randint(0, 999999):06d}'
    EmailConfirmation.objects.update_or_create(user=user, defaults={'code': code})
    send_mail(
        'Код подтверждения Werewolf',
        f'Твой код подтверждения: {code}',
        None, [email], fail_silently=False,
    )


def login_view(request):
    if request.user.is_authenticated:
        return redirect('shop:profile')
    if request.method == 'POST':
        form = LoginForm(request.POST)
        if form.is_valid():
            email = form.cleaned_data['email']
            password = form.cleaned_data['password']
            existing = User.objects.filter(email=email).first()
            if existing and not existing.is_active and existing.check_password(password):
                _send_confirmation(existing, email)
                request.session['pending_email'] = email
                messages.info(request, f'Аккаунт не подтверждён. Новый код отправлен на {email}.')
                return redirect('shop:confirm')
            user = authenticate(request, username=email, password=password)
            if user is None:
                messages.error(request, 'Неверный email или пароль')
            else:
                auth_login(request, user)
                return redirect('shop:profile')
    else:
        form = LoginForm()
    return render(request, 'shop/auth/login.html', {'form': form})


def logout_view(request):
    auth_logout(request)
    return redirect('shop:home')


@login_required
def profile(request):
    profile_obj, _ = Profile.objects.get_or_create(user=request.user)
    if request.method == 'POST':
        form = ProfileForm(request.POST, instance=profile_obj)
        if form.is_valid():
            form.save()
            messages.success(request, 'Профиль обновлён')
            return redirect('shop:profile')
    else:
        form = ProfileForm(instance=profile_obj)

    orders = Order.objects.filter(user=request.user).prefetch_related('items')
    return render(request, 'shop/profile.html', {
        'form': form,
        'orders': orders,
    })

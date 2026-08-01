from django.db.models import Sum

from apps.cart.models import Cart

SESSION_CART_COUNT_KEY = "cart_item_count"


def refresh_cart_item_count(request, cart=None):
    """Store the badge count in the session so every page avoids a DB hit."""
    try:
        if cart is None:
            qs = Cart.objects.all()
            if request.user.is_authenticated:
                qs = qs.filter(user=request.user)
            elif request.session.session_key:
                qs = qs.filter(session_key=request.session.session_key, user__isnull=True)
            else:
                request.session[SESSION_CART_COUNT_KEY] = 0
                return 0
            cart = qs.first()
        count = 0
        if cart is not None:
            count = cart.items.aggregate(total=Sum("quantity"))["total"] or 0
        request.session[SESSION_CART_COUNT_KEY] = count
        return count
    except Exception:
        request.session[SESSION_CART_COUNT_KEY] = 0
        return 0


def cart_context(request):
    if SESSION_CART_COUNT_KEY in request.session:
        return {"CART_ITEM_COUNT": request.session.get(SESSION_CART_COUNT_KEY) or 0}
    return {"CART_ITEM_COUNT": refresh_cart_item_count(request)}

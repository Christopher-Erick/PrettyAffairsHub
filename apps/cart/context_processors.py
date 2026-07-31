from apps.cart.models import Cart


def cart_context(request):
    count = 0
    try:
        if request.user.is_authenticated:
            cart = Cart.objects.filter(user=request.user).prefetch_related("items").first()
        elif request.session.session_key:
            cart = (
                Cart.objects.filter(session_key=request.session.session_key, user__isnull=True)
                .prefetch_related("items")
                .first()
            )
        else:
            cart = None
        if cart:
            count = sum(i.quantity for i in cart.items.all())
    except Exception:
        count = 0
    return {"CART_ITEM_COUNT": count}

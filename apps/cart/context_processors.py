from django.db.models import Sum

from apps.cart.models import Cart


def cart_context(request):
    count = 0
    try:
        qs = Cart.objects.all()
        if request.user.is_authenticated:
            qs = qs.filter(user=request.user)
        elif request.session.session_key:
            qs = qs.filter(session_key=request.session.session_key, user__isnull=True)
        else:
            return {"CART_ITEM_COUNT": 0}
        count = qs.aggregate(total=Sum("items__quantity"))["total"] or 0
    except Exception:
        count = 0
    return {"CART_ITEM_COUNT": count}

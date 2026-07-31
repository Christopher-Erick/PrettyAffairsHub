from apps.accounts.models import Wishlist


def get_or_create_wishlist(user):
    wishlist, _ = Wishlist.objects.get_or_create(user=user)
    return wishlist


def toggle_wishlist(user, product):
    wishlist = get_or_create_wishlist(user)
    if wishlist.products.filter(pk=product.pk).exists():
        wishlist.products.remove(product)
        return False
    wishlist.products.add(product)
    return True

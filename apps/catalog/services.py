RECENTLY_VIEWED_KEY = "recently_viewed"
MAX_RECENT = 12


def track_product_view(request, product_id):
    viewed = request.session.get(RECENTLY_VIEWED_KEY, [])
    product_id = int(product_id)
    viewed = [pid for pid in viewed if pid != product_id]
    viewed.insert(0, product_id)
    request.session[RECENTLY_VIEWED_KEY] = viewed[:MAX_RECENT]
    request.session.modified = True


def get_recently_viewed_ids(request):
    return request.session.get(RECENTLY_VIEWED_KEY, [])

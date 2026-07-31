"""Resolve swatch colours for product shades.

Shade names are matched against known colour vocabulary first: source photos are
often dominated by packaging or a shared studio background, which makes several
shades of one product sample to the same colour. Names such as "Riri" or "Xoxo"
carry no colour, so those fall back to sampling the shade image.
"""

from __future__ import annotations

import colorsys
from collections import defaultdict

try:
    from PIL import Image
except ImportError:  # pragma: no cover - Pillow ships with the project
    Image = None


NEUTRAL_FALLBACK = "#C9A39A"

SHADE_KEYWORDS = {
    "clear": "#E9DCD6",
    "transparent": "#E9DCD6",
    "crystal": "#E6DAD6",
    "ivory": "#EADFD2",
    "vanilla": "#E4D3B8",
    "cream": "#E6D5BE",
    "coconut": "#E7DCC8",
    "colada": "#E4D2B4",
    "champagne": "#DCC195",
    "macadamia": "#D9BE95",
    "almond": "#C9A182",
    "cashew": "#C6A583",
    "sesame": "#C2A180",
    "buff": "#C4A183",
    "beige": "#BE9C82",
    "sand": "#BE9C82",
    "taupe": "#A38B7C",
    "mushroom": "#9C8577",
    "nude": "#B98269",
    "blush": "#D98D8D",
    "ballet": "#DFA0A6",
    "peach": "#E99B7B",
    "apricot": "#E19566",
    "papaya": "#E4864F",
    "guava": "#DE6E6A",
    "coral": "#E96F62",
    "melon": "#E2705F",
    "watermelon": "#DA4A5C",
    "punch": "#CE3F5C",
    "candy": "#E15C86",
    "bubblegum": "#E86C99",
    "pink": "#D86C91",
    "fuchsia": "#C7407F",
    "fuschia": "#C7407F",
    "magenta": "#B93379",
    "rose": "#B25765",
    "rosewood": "#8E4A4C",
    "raspberry": "#A32048",
    "strawberry": "#BE2C43",
    "cherry": "#A71930",
    "ruby": "#9E1B32",
    "scarlet": "#B32330",
    "red": "#B8222E",
    "crimson": "#991E32",
    "brick": "#9C4234",
    "terracotta": "#A0533C",
    "goji": "#9E2B2F",
    "currant": "#7C2138",
    "merlot": "#6E1F33",
    "sangria": "#75203C",
    "wine": "#711F3A",
    "burgundy": "#6C1F33",
    "berry": "#8D294C",
    "acai": "#6B2E5F",
    "plum": "#713B5B",
    "grape": "#6A3B65",
    "mauve": "#9A6A78",
    "purple": "#714B76",
    "lavender": "#9A85AE",
    "orange": "#D86C31",
    "tangerine": "#DD7434",
    "honey": "#C7954F",
    "caramel": "#A9713F",
    "toffee": "#96603A",
    "butter": "#D8B96B",
    "gold": "#C29A52",
    "lemon": "#D7BE5A",
    "pineapple": "#E8C64A",
    "lime": "#A5B95C",
    "cucum": "#7EA46B",
    "green": "#5A865F",
    "mint": "#8FBBA2",
    "blue": "#4F6F91",
    "toast": "#8A5648",
    "toasted": "#8A5648",
    "tan": "#9A674F",
    "latte": "#A67B5B",
    "mocha": "#7C5344",
    "coffee": "#6A4436",
    "espresso": "#4E332B",
    "cacao": "#5B3A30",
    "cocoa": "#694037",
    "chocolate": "#5D3A2E",
    "chocolit": "#5D3A2E",
    "brownie": "#5A3A30",
    "truffle": "#553A32",
    "hazelnut": "#8A6046",
    "maple": "#8D503D",
    "brown": "#6F4336",
    "black": "#2A2320",
}


def _hex(red: float, green: float, blue: float) -> str:
    return f"#{round(red):02X}{round(green):02X}{round(blue):02X}"


def color_from_name(name: str) -> str | None:
    """Match a shade name against known colour vocabulary."""
    lowered = (name or "").lower()
    matches = [
        (lowered.index(keyword), -len(keyword), color)
        for keyword, color in SHADE_KEYWORDS.items()
        if keyword in lowered
    ]
    if not matches:
        return None
    return min(matches)[2]


def color_from_image(source, *, sample: int = 180) -> str | None:
    """Pick the dominant product colour from a shade image."""
    if Image is None:
        return None
    try:
        with Image.open(source) as opened:
            image = opened.convert("RGB")
            image.thumbnail((sample, sample))
            width, height = image.size
            inset_x, inset_y = int(width * 0.16), int(height * 0.16)
            image = image.crop((inset_x, inset_y, width - inset_x, height - inset_y))
            pixels = list(image.getdata())
    except Exception:
        return None

    buckets: dict[tuple[int, int, int], list[int]] = defaultdict(lambda: [0, 0, 0, 0])
    for red, green, blue in pixels:
        high, low = max(red, green, blue), min(red, green, blue)
        if high > 242 and high - low < 24:
            continue
        if high < 28:
            continue
        if high - low < 12 and not 45 < high < 205:
            continue
        bucket = buckets[(red >> 4, green >> 4, blue >> 4)]
        bucket[0] += 1
        bucket[1] += red
        bucket[2] += green
        bucket[3] += blue

    if not buckets:
        return None

    def score(entry) -> float:
        count, red_sum, green_sum, blue_sum = entry[1]
        red, green, blue = red_sum / count, green_sum / count, blue_sum / count
        high, low = max(red, green, blue), min(red, green, blue)
        saturation = (high - low) / high if high else 0
        return count * (0.4 + saturation * 2.0)

    count, red_sum, green_sum, blue_sum = max(buckets.items(), key=score)[1]
    red, green, blue = red_sum / count, green_sum / count, blue_sum / count

    hue, lightness, saturation = colorsys.rgb_to_hls(red / 255, green / 255, blue / 255)
    saturation = min(max(saturation, 0.2), 0.95)
    lightness = min(max(lightness, 0.24), 0.8)
    red, green, blue = colorsys.hls_to_rgb(hue, lightness, saturation)
    return _hex(red * 255, green * 255, blue * 255)


def resolve_shade_color(name: str, image_field=None) -> str:
    """Best available colour for a shade: its name, then its image."""
    named = color_from_name(name)
    if named:
        return named
    if image_field:
        try:
            with image_field.open("rb") as handle:
                sampled = color_from_image(handle)
        except Exception:
            sampled = None
        if sampled:
            return sampled
    return NEUTRAL_FALLBACK

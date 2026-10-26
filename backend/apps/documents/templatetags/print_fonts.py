"""{% font_face %} gives a print template the Satoshi font (files in backend/assets/fonts/)."""
from django import template
from django.conf import settings
from django.utils.safestring import mark_safe

register = template.Library()

FILES = {400: "Satoshi-Regular.otf", 500: "Satoshi-Medium.otf", 700: "Satoshi-Bold.otf"}


@register.simple_tag
def font_face():
    folder = settings.BASE_DIR / "assets" / "fonts"
    return mark_safe("".join(
        f'@font-face {{ font-family: "Satoshi"; font-weight: {weight}; src: url("{(folder / name).as_uri()}"); }}\n'
        for weight, name in FILES.items()))

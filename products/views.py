from django.shortcuts import render

from .forms import ProductFilterForm
from .models import Product
from .querysets import TAG_MODE_ANY, filter_products


def product_list(request):
    data = request.GET.copy()
    if not data.get("tag_mode"):
        # Without this, no Any/All radio is selected when the URL omits the mode.
        data["tag_mode"] = TAG_MODE_ANY
    form = ProductFilterForm(data)

    if form.is_valid():
        # Two queries: products joined to their category, then all their tags.
        queryset = Product.objects.select_related("category").prefetch_related("tags")
        products = list(filter_products(queryset, form.cleaned_data))
    else:
        # Invalid filters show their errors rather than quietly widening the search.
        products = []

    return render(
        request, "products/product_list.html", {"form": form, "products": products}
    )

from django.core.paginator import Paginator
from django.shortcuts import render

from .forms import ProductFilterForm
from .models import Product
from .querysets import TAG_MODE_ANY, filter_products

PAGE_SIZE = 10


def product_list(request):
    """List products, filtered by the query string, one page at a time.

    The steps are: validate the filters, build the queryset, order it, then
    paginate. Products are currently ordered by Product.Meta.ordering (name,
    then primary key).

    To let users choose the order later, add a validated sort parameter that
    accepts only values from a fixed allowlist, apply it before paginating, and
    keep the primary key last so ties stay in a stable order. Never pass a raw
    query-string value to order_by().
    """
    data = request.GET.copy()
    if not data.get("tag_mode"):
        # Without this, no Any/All radio is selected when the URL omits the mode.
        data["tag_mode"] = TAG_MODE_ANY
    form = ProductFilterForm(data)

    if form.is_valid():
        # Results are not cached: the filter, tag mode and page combinations
        # are many, so hit rates would be low, and stale results cost more than
        # these queries. If profiling ever shows a need, key the cache on the
        # validated filters (with sorted tag ids), tag mode, ordering and page,
        # and clear it when products, categories, tags or their links change,
        # including bulk imports.
        queryset = filter_products(
            Product.objects.select_related("category").prefetch_related("tags"),
            form.cleaned_data,
        )
        paginator = Paginator(queryset, PAGE_SIZE)
    else:
        # Invalid filters show their errors rather than quietly widening the search.
        paginator = Paginator([], PAGE_SIZE)

    # A missing or non-numeric page is page 1; one out of range is the last page.
    page = paginator.get_page(request.GET.get("page"))
    page_numbers = paginator.get_elided_page_range(
        page.number, on_each_side=2, on_ends=1
    )

    return render(
        request,
        "products/product_list.html",
        {"form": form, "page": page, "page_numbers": page_numbers},
    )

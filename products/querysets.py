from django.db.models import Exists, OuterRef

from .models import Product

TAG_MODE_ANY = "any"
TAG_MODE_ALL = "all"


def filter_products(queryset, filters):
    """Narrow a product queryset using validated filter values.

    Every filter must match, and a missing or empty filter has no effect:

    - q: case-insensitive substring match on the description only.
    - category: the product belongs to this category.
    - tags: with tag_mode "any" (the default) the product has at least one of
      the tags; with "all" it has all of them.
    """
    q = filters.get("q")
    if q:
        # Kept simple for a take-home: a leading-wildcard LIKE scans every row.
        # At scale, use PostgreSQL full-text search (SearchVector and
        # SearchQuery on a GIN index) or pg_trgm for substring matches.
        queryset = queryset.filter(description__icontains=q)

    category = filters.get("category")
    if category:
        queryset = queryset.filter(category=category)

    tags = filters.get("tags")
    if tags:
        if filters.get("tag_mode") == TAG_MODE_ALL:
            # One filter() per tag, so each tag gets its own join and "has A"
            # and "has B" are checked separately. In a single call, one row
            # would have to be both tags at once. At scale, a GROUP BY with
            # HAVING COUNT avoids one join per selected tag.
            for tag in tags:
                queryset = queryset.filter(tags=tag)
        else:
            # A subquery rather than a join, so a product with several matching
            # tags is still one row and no DISTINCT is needed.
            has_a_selected_tag = Product.tags.through.objects.filter(
                product=OuterRef("pk"), tag__in=tags
            )
            queryset = queryset.filter(Exists(has_a_selected_tag))

    return queryset

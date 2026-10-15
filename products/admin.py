from django.contrib import admin

from .models import Category, Product, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    search_fields = ["name"]


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    # Tags are left out of list_display: showing them costs a query per row.
    list_display = ["name", "category"]
    list_select_related = ["category"]
    list_filter = ["category"]
    # Tag names are searchable instead of listed as a filter: a sidebar of every
    # tag stops being usable once there are many.
    search_fields = ["name", "description", "tags__name"]
    # A search box rather than a pick-list of every tag.
    autocomplete_fields = ["tags"]

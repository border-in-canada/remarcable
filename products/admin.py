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
    list_filter = ["category", "tags"]
    search_fields = ["name", "description"]
    filter_horizontal = ["tags"]

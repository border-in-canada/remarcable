from django.db import models
from django.db.models.functions import Lower


class Category(models.Model):
    name = models.CharField(max_length=100)

    class Meta:
        ordering = ["name"]
        verbose_name_plural = "categories"
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="category_name_ci_unique",
                violation_error_message="A category with this name already exists.",
            )
        ]

    def __str__(self):
        return self.name


class Tag(models.Model):
    name = models.CharField(max_length=50)

    class Meta:
        ordering = ["name"]
        constraints = [
            models.UniqueConstraint(
                Lower("name"),
                name="tag_name_ci_unique",
                violation_error_message="A tag with this name already exists.",
            )
        ]

    def __str__(self):
        return self.name


class Product(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    category = models.ForeignKey(
        Category, on_delete=models.PROTECT, related_name="products"
    )
    tags = models.ManyToManyField(Tag, blank=True, related_name="products")

    class Meta:
        ordering = ["name", "pk"]

    def __str__(self):
        return self.name

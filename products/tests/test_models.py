from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.db.models import ProtectedError
from django.test import TestCase
from django.urls import reverse

from products.models import Category, Product, Tag


class CategoryModelTests(TestCase):
    def test_str_is_name(self):
        self.assertEqual(str(Category(name="Kitchen")), "Kitchen")

    def test_name_must_be_unique(self):
        Category.objects.create(name="Kitchen")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="Kitchen")

    def test_name_uniqueness_ignores_case(self):
        Category.objects.create(name="Kitchen")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Category.objects.create(name="kitchen")

    def test_duplicate_name_gives_a_validation_message(self):
        Category.objects.create(name="Kitchen")
        with self.assertRaisesMessage(
            ValidationError, "A category with this name already exists."
        ):
            Category(name="KITCHEN").validate_constraints()

    def test_ordered_by_name(self):
        Category.objects.create(name="Toys")
        Category.objects.create(name="Books")
        self.assertEqual(
            list(Category.objects.values_list("name", flat=True)), ["Books", "Toys"]
        )


class TagModelTests(TestCase):
    def test_str_is_name(self):
        self.assertEqual(str(Tag(name="eco")), "eco")

    def test_name_must_be_unique(self):
        Tag.objects.create(name="eco")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Tag.objects.create(name="eco")

    def test_name_uniqueness_ignores_case(self):
        Tag.objects.create(name="eco")
        with self.assertRaises(IntegrityError), transaction.atomic():
            Tag.objects.create(name="ECO")

    def test_duplicate_name_gives_a_validation_message(self):
        Tag.objects.create(name="eco")
        with self.assertRaisesMessage(
            ValidationError, "A tag with this name already exists."
        ):
            Tag(name="Eco").validate_constraints()


class ProductModelTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Kitchen")
        cls.eco = Tag.objects.create(name="eco")
        cls.sale = Tag.objects.create(name="sale")

    def make_product(self, name="Kettle", **kwargs):
        return Product.objects.create(
            name=name,
            description="Boils water.",
            category=kwargs.pop("category", self.category),
            **kwargs,
        )

    def test_str_is_name(self):
        self.assertEqual(str(self.make_product("Kettle")), "Kettle")

    def test_category_is_required(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            Product.objects.create(name="Orphan", description="No category.")

    def test_category_with_products_cannot_be_deleted(self):
        self.make_product()
        with self.assertRaises(ProtectedError):
            self.category.delete()

    def test_category_without_products_can_be_deleted(self):
        self.category.delete()
        self.assertFalse(Category.objects.exists())

    def test_product_can_have_several_tags(self):
        product = self.make_product()
        product.tags.set([self.eco, self.sale])
        self.assertEqual(set(product.tags.all()), {self.eco, self.sale})
        self.assertEqual(list(self.eco.products.all()), [product])

    def test_product_can_have_no_tags(self):
        self.assertFalse(self.make_product().tags.exists())

    def test_category_reverse_relation(self):
        product = self.make_product()
        self.assertEqual(list(self.category.products.all()), [product])

    def test_ordering_is_by_name_then_pk(self):
        second = self.make_product("Pan")
        first = self.make_product("Pan")
        earlier = self.make_product("Kettle")
        self.assertEqual(list(Product.objects.all()), [earlier, second, first])


class ProductAdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Kitchen")
        cls.eco = Tag.objects.create(name="eco")
        cls.sale = Tag.objects.create(name="sale")
        cls.admin_user = get_user_model().objects.create_superuser(
            username="admin", password="not-a-real-password"
        )

    def setUp(self):
        self.client.force_login(self.admin_user)

    def test_changelist_loads_with_search_and_filters(self):
        url = reverse("admin:products_product_changelist")
        response = self.client.get(url, {"q": "kettle", "tags__id__exact": self.eco.pk})
        self.assertEqual(response.status_code, 200)

    def test_duplicate_category_name_shows_a_message_in_admin(self):
        response = self.client.post(
            reverse("admin:products_category_add"), {"name": "kitchen"}
        )
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "A category with this name already exists.")
        self.assertEqual(Category.objects.count(), 1)

    def test_product_with_several_tags_can_be_created(self):
        response = self.client.post(
            reverse("admin:products_product_add"),
            {
                "name": "Kettle",
                "description": "Boils water.",
                "category": self.category.pk,
                "tags": [self.eco.pk, self.sale.pk],
            },
        )
        self.assertEqual(response.status_code, 302)
        product = Product.objects.get(name="Kettle")
        self.assertEqual(set(product.tags.all()), {self.eco, self.sale})

from django.db import connection
from django.test.utils import CaptureQueriesContext
from django.urls import reverse

from products.models import Product
from products.querysets import TAG_MODE_ALL, TAG_MODE_ANY
from products.tests import test_filters


class ProductListViewTests(test_filters.FilterTestCase):
    ALL_NAMES = ["Hose", "Kettle", "Pan", "Shovel", "Toaster", "Water Jug"]

    def get(self, **params):
        return self.client.get(reverse("products:product_list"), params)

    def shown(self, response):
        return [product.name for product in response.context["products"]]

    def test_page_is_served_at_the_site_root(self):
        self.assertEqual(reverse("products:product_list"), "/")
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertTemplateUsed(response, "products/product_list.html")

    def test_lists_every_product_by_default(self):
        response = self.get()
        self.assertEqual(self.shown(response), self.ALL_NAMES)
        self.assertContains(response, "6 products found")

    def test_shows_a_product_with_its_category_and_tags(self):
        response = self.get(q="boils")
        self.assertContains(response, "1 product found")
        self.assertContains(response, "<h2>Kettle</h2>", html=True)
        self.assertContains(response, "Category: Kitchen")
        for tag in ("gift", "sale", "popular"):
            self.assertContains(response, f"<li>{tag}</li>", html=True)

    def test_any_is_selected_when_the_mode_is_missing_or_blank(self):
        for params in ({}, {"tag_mode": ""}):
            with self.subTest(params=params):
                response = self.get(**params)
                self.assertEqual(response.context["form"]["tag_mode"].value(), "any")
                self.assertContains(response, "checked", count=1)

    def test_submitted_filters_stay_selected(self):
        response = self.get(
            q="boils",
            category=self.kitchen.pk,
            tags=[self.gift.pk, self.sale.pk],
            tag_mode=TAG_MODE_ALL,
        )
        self.assertContains(response, 'value="boils"')
        self.assertContains(response, f'<option value="{self.kitchen.pk}" selected>')
        # Two tag checkboxes and the "all" radio button.
        self.assertContains(response, "checked", count=3)

    def test_filters_combine_in_both_tag_modes(self):
        both = [self.gift.pk, self.sale.pk]
        cases = [
            ({"tags": both, "tag_mode": TAG_MODE_ALL}, ["Hose", "Kettle"]),
            (
                {"category": self.kitchen.pk, "tags": both, "tag_mode": TAG_MODE_ALL},
                ["Kettle"],
            ),
            (
                {"category": self.kitchen.pk, "tags": both, "tag_mode": TAG_MODE_ANY},
                ["Kettle", "Pan", "Toaster"],
            ),
            ({"q": "boils", "tags": [self.gift.pk]}, ["Kettle"]),
            ({"q": "boils", "tags": [self.new.pk]}, []),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                self.assertEqual(self.shown(self.get(**params)), expected)

    def test_invalid_filters_show_errors_and_no_products(self):
        for params in ({"category": "99999"}, {"tag_mode": "some"}, {"tags": "abc"}):
            with self.subTest(params=params):
                response = self.get(**params)
                self.assertEqual(response.status_code, 200)
                self.assertEqual(self.shown(response), [])
                self.assertContains(response, "Fix the errors above")
                self.assertNotContains(response, "found")

    def test_no_matches_shows_a_message(self):
        response = self.get(q="zzz")
        self.assertContains(response, "0 products found")
        self.assertContains(response, "No products match your search.")

    def test_reset_link_returns_to_the_unfiltered_page(self):
        response = self.get(q="boils")
        self.assertContains(response, '<a href="/">Reset</a>', html=True)

    def test_product_text_is_escaped(self):
        Product.objects.create(
            name="<b>Bold</b>",
            description="<script>alert(1)</script>",
            category=self.kitchen,
        )
        response = self.get()
        self.assertContains(response, "&lt;script&gt;alert(1)&lt;/script&gt;")
        self.assertNotContains(response, "<script>alert(1)</script>")


class ProductListQueryTests(test_filters.FilterTestCase):
    def requests(self):
        return [
            {},
            {"tags": [self.gift.pk, self.sale.pk], "tag_mode": TAG_MODE_ANY},
            {"tags": [self.gift.pk, self.sale.pk], "tag_mode": TAG_MODE_ALL},
        ]

    def queries_for(self, params):
        with CaptureQueriesContext(connection) as captured:
            self.client.get(reverse("products:product_list"), params)
        return [query["sql"] for query in captured]

    def test_products_load_in_two_queries(self):
        # One for products with their category, one for all their tags. The form's
        # category and tag choices are separate queries on other tables.
        for params in self.requests():
            with self.subTest(params=params):
                sql = self.queries_for(params)
                self.assertEqual(sum("products_product" in q for q in sql), 2)

    def test_query_count_does_not_grow_with_the_number_of_products(self):
        before = [len(self.queries_for(params)) for params in self.requests()]
        for number in range(10):
            product = Product.objects.create(
                name=f"Extra {number}", description="More.", category=self.garden
            )
            product.tags.set([self.gift, self.sale])
        after = [len(self.queries_for(params)) for params in self.requests()]
        self.assertEqual(before, after)

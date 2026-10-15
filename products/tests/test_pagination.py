import html
import re
from urllib.parse import parse_qs, urlsplit

from django.db import connection
from django.test import TestCase
from django.test.utils import CaptureQueriesContext

from products.models import Category, Product, Tag
from products.views import PAGE_SIZE


def link_query(response, rel):
    """Query-string values of the page link with this rel ("prev" or "next")."""
    content = response.content.decode()
    match = re.search(rf'<a href="([^"]*)" rel="{rel}">', content)
    assert match, f"no {rel} link on the page"
    return parse_qs(urlsplit(html.unescape(match.group(1))).query)


class PaginationTestCase(TestCase):
    """Products 01-25. Odd numbers have tag "a"; multiples of 3 have tag "b"."""

    @classmethod
    def setUpTestData(cls):
        cls.category = Category.objects.create(name="Kitchen")
        cls.tag_a = Tag.objects.create(name="a")
        cls.tag_b = Tag.objects.create(name="b")
        for number in range(1, 26):
            product = Product.objects.create(
                name=f"Product {number:02d}",
                description=f"Item {number:02d}",
                category=cls.category,
            )
            if number % 2:
                product.tags.add(cls.tag_a)
            if number % 3 == 0:
                product.tags.add(cls.tag_b)

    @staticmethod
    def name(number):
        return f"Product {number:02d}"

    def get(self, **params):
        return self.client.get("/", params)

    def walk(self, **params):
        """Names on each page, from the first page to the last."""
        first = self.get(**params)
        pages = [[p.name for p in first.context["page"]]]
        for number in range(2, first.context["page"].paginator.num_pages + 1):
            response = self.get(page=number, **params)
            pages.append([p.name for p in response.context["page"]])
        return pages


class PaginationTests(PaginationTestCase):
    def test_pages_hold_ten_products_and_cover_every_product_once(self):
        self.assertEqual(PAGE_SIZE, 10)
        pages = self.walk()
        self.assertEqual([len(page) for page in pages], [10, 10, 5])
        self.assertEqual(
            [name for page in pages for name in page],
            [self.name(n) for n in range(1, 26)],
        )

    def test_total_and_position_are_shown(self):
        response = self.get(page=2)
        self.assertContains(response, "25 products found")
        self.assertContains(response, "Page 2 of 3")

    def test_missing_or_non_numeric_page_is_the_first_page(self):
        for value in ("", "abc", "1.5"):
            with self.subTest(page=value):
                self.assertEqual(self.get(page=value).context["page"].number, 1)
        self.assertEqual(self.client.get("/").context["page"].number, 1)

    def test_out_of_range_page_is_the_last_page(self):
        for value in ("0", "-1", "4", "999"):
            with self.subTest(page=value):
                self.assertEqual(self.get(page=value).context["page"].number, 3)

    def test_no_product_repeats_across_pages_in_either_tag_mode(self):
        numbers = range(1, 26)
        odd = {n for n in numbers if n % 2}
        multiples_of_three = {n for n in numbers if n % 3 == 0}
        cases = [
            ({"tags": [self.tag_a.pk], "tag_mode": "all"}, odd),
            (
                {"tags": [self.tag_a.pk, self.tag_b.pk], "tag_mode": "any"},
                odd | multiples_of_three,
            ),
            (
                {"tags": [self.tag_a.pk, self.tag_b.pk], "tag_mode": "all"},
                odd & multiples_of_three,
            ),
        ]
        for params, expected in cases:
            with self.subTest(params=params):
                names = [name for page in self.walk(**params) for name in page]
                self.assertEqual(names, [self.name(n) for n in sorted(expected)])

    def test_navigation_is_hidden_when_everything_fits_on_one_page(self):
        response = self.get(q="Item 0")
        self.assertEqual(len(response.context["page"]), 9)
        self.assertNotContains(response, 'class="pagination"')

    def test_navigation_is_hidden_when_there_are_no_products(self):
        for params in ({"q": "zzz"}, {"category": "99999"}):
            with self.subTest(params=params):
                self.assertNotContains(self.get(**params), 'class="pagination"')


class PaginationLinkTests(PaginationTestCase):
    def test_links_keep_every_filter_and_change_only_the_page(self):
        params = {
            "q": "Item",
            "category": self.category.pk,
            "tags": [self.tag_a.pk, self.tag_b.pk],
            "tag_mode": "any",
        }
        for response, rel, page in (
            (self.get(**params), "next", "2"),
            (self.get(page=2, **params), "prev", "1"),
        ):
            with self.subTest(rel=rel):
                query = link_query(response, rel)
                self.assertEqual(query["q"], ["Item"])
                self.assertEqual(query["category"], [str(self.category.pk)])
                self.assertCountEqual(
                    query["tags"], [str(self.tag_a.pk), str(self.tag_b.pk)]
                )
                self.assertEqual(query["tag_mode"], ["any"])
                self.assertEqual(query["page"], [page])

    def test_links_encode_special_characters_in_the_search_text(self):
        for number in range(11):
            Product.objects.create(
                name=f"Cartoon {number}",
                description=f"Tom & Jerry #{number}",
                category=self.category,
            )
        response = self.get(q="Tom & Jerry")
        self.assertEqual(response.context["page"].paginator.num_pages, 2)
        self.assertEqual(link_query(response, "next")["q"], ["Tom & Jerry"])

    def test_search_form_does_not_carry_the_page_number(self):
        # A new search therefore starts from the first page.
        self.assertNotContains(self.get(page=2), 'name="page"')

    def test_long_page_lists_are_shortened(self):
        Product.objects.bulk_create(
            Product(name=f"Bulk {n:03d}", description="Bulk", category=self.category)
            for n in range(95)
        )
        response = self.get(page=6)
        self.assertEqual(response.context["page"].paginator.num_pages, 12)
        self.assertContains(response, "…")
        for linked in (1, 4, 8, 12):
            self.assertContains(response, f'page={linked}"')
        for skipped in (2, 3, 9, 10):
            self.assertNotContains(response, f'page={skipped}"')


class TiedNamesTests(TestCase):
    def test_products_with_the_same_name_keep_a_stable_order_across_pages(self):
        category = Category.objects.create(name="Kitchen")
        created = [
            Product.objects.create(name="Same", description="x", category=category)
            for _ in range(15)
        ]
        first = [p.pk for p in self.client.get("/").context["page"]]
        second = [p.pk for p in self.client.get("/", {"page": 2}).context["page"]]
        self.assertEqual(first + second, [p.pk for p in created])


class PaginationQueryTests(PaginationTestCase):
    def product_queries(self, **params):
        with CaptureQueriesContext(connection) as captured:
            self.get(**params)
        return sum("products_product" in query["sql"] for query in captured)

    def requests(self):
        both = [self.tag_a.pk, self.tag_b.pk]
        return [
            {},
            {"page": 3},
            {"tags": both, "tag_mode": "any"},
            {"tags": both, "tag_mode": "any", "page": 2},
            {"tags": both, "tag_mode": "all"},
        ]

    def test_a_page_takes_three_product_queries_whatever_the_size(self):
        # The total count, the page of products with categories, and their tags.
        for params in self.requests():
            with self.subTest(params=params):
                self.assertEqual(self.product_queries(**params), 3)

        Product.objects.bulk_create(
            Product(name=f"More {n:03d}", description="x", category=self.category)
            for n in range(200)
        )
        for params in self.requests():
            with self.subTest(params=params, size="larger"):
                self.assertEqual(self.product_queries(**params), 3)

    def test_invalid_filters_run_no_product_queries(self):
        self.assertEqual(self.product_queries(category="99999"), 0)

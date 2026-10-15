from django.http import QueryDict
from django.test import TestCase

from products.forms import ProductFilterForm
from products.models import Category, Product, Tag
from products.querysets import TAG_MODE_ALL, TAG_MODE_ANY, filter_products


class FilterTestCase(TestCase):
    """
    Product         Category  Tags
    Kettle          Kitchen   gift, sale, popular
    Toaster         Kitchen   gift, popular
    Pan             Kitchen   sale, handmade
    Hose            Garden    gift, sale, new
    Shovel          Garden    handmade
    Water Jug       Kitchen   (none)   -- "water" appears only in its name
    """

    @classmethod
    def setUpTestData(cls):
        kitchen = Category.objects.create(name="Kitchen")
        garden = Category.objects.create(name="Garden")
        cls.kitchen, cls.garden = kitchen, garden
        cls.gift = Tag.objects.create(name="gift")
        cls.sale = Tag.objects.create(name="sale")
        cls.new = Tag.objects.create(name="new")
        cls.handmade = Tag.objects.create(name="handmade")
        cls.popular = Tag.objects.create(name="popular")

        def add(name, description, category, *tags):
            product = Product.objects.create(
                name=name, description=description, category=category
            )
            product.tags.set(tags)

        add(
            "Kettle",
            "Stainless steel kettle that boils water fast",
            kitchen,
            cls.gift,
            cls.sale,
            cls.popular,
        )
        add("Toaster", "Toasts bread evenly", kitchen, cls.gift, cls.popular)
        add("Pan", "Non-stick frying pan", kitchen, cls.sale, cls.handmade)
        add("Hose", "Flexible garden hose, 20m", garden, cls.gift, cls.sale, cls.new)
        add("Shovel", "Sturdy shovel for digging", garden, cls.handmade)
        add("Water Jug", "Holds a litre", kitchen)

    def names(self, **filters):
        return [p.name for p in filter_products(Product.objects.all(), filters)]


class FilterProductsTests(FilterTestCase):
    ALL_NAMES = ["Hose", "Kettle", "Pan", "Shovel", "Toaster", "Water Jug"]

    def test_no_filters_returns_every_product(self):
        self.assertEqual(self.names(), self.ALL_NAMES)

    def test_empty_filter_values_have_no_effect(self):
        empty = {"q": "", "category": None, "tags": [], "tag_mode": TAG_MODE_ANY}
        self.assertEqual(self.names(**empty), self.ALL_NAMES)

    def test_description_search(self):
        cases = {
            "boils": ["Kettle"],
            "BOILS": ["Kettle"],  # case-insensitive
            "oil": ["Kettle"],  # substring, not whole word
            "garden": ["Hose"],
            "zzz": [],
        }
        for q, expected in cases.items():
            with self.subTest(q=q):
                self.assertEqual(self.names(q=q), expected)

    def test_search_ignores_the_product_name(self):
        # "Water Jug" is named after water; only the Kettle's description says so.
        self.assertEqual(self.names(q="water"), ["Kettle"])
        self.assertEqual(self.names(q="jug"), [])

    def test_category_filter(self):
        self.assertEqual(self.names(category=self.garden), ["Hose", "Shovel"])
        self.assertEqual(
            self.names(category=self.kitchen), ["Kettle", "Pan", "Toaster", "Water Jug"]
        )

    def test_any_tag_matches_products_with_at_least_one_tag(self):
        cases = {
            (self.gift,): ["Hose", "Kettle", "Toaster"],
            (self.new,): ["Hose"],
            (self.gift, self.sale): ["Hose", "Kettle", "Pan", "Toaster"],
            (self.handmade, self.popular): ["Kettle", "Pan", "Shovel", "Toaster"],
        }
        for tags, expected in cases.items():
            with self.subTest(tags=[t.name for t in tags]):
                self.assertEqual(self.names(tags=tags, tag_mode=TAG_MODE_ANY), expected)

    def test_any_tag_is_the_default_mode(self):
        self.assertEqual(
            self.names(tags=[self.gift, self.sale]),
            self.names(tags=[self.gift, self.sale], tag_mode=TAG_MODE_ANY),
        )

    def test_any_tag_lists_a_product_once_however_many_tags_match(self):
        names = self.names(tags=[self.gift, self.sale, self.new], tag_mode=TAG_MODE_ANY)
        self.assertEqual(names.count("Hose"), 1)
        self.assertEqual(names, ["Hose", "Kettle", "Pan", "Toaster"])

    def test_all_tags_matches_only_products_with_every_tag(self):
        cases = {
            (self.gift,): ["Hose", "Kettle", "Toaster"],
            (self.gift, self.sale): ["Hose", "Kettle"],
            (self.gift, self.sale, self.new): ["Hose"],
            (self.sale, self.new): ["Hose"],
            (self.gift, self.popular): ["Kettle", "Toaster"],
            (self.sale, self.handmade): ["Pan"],
        }
        for tags, expected in cases.items():
            with self.subTest(tags=[t.name for t in tags]):
                self.assertEqual(self.names(tags=tags, tag_mode=TAG_MODE_ALL), expected)

    def test_all_tags_with_no_common_product_is_empty(self):
        # Only the Hose has "new", and it is not in the Kitchen category.
        self.assertEqual(
            self.names(
                tags=[self.new, self.sale],
                tag_mode=TAG_MODE_ALL,
                category=self.kitchen,
            ),
            [],
        )

    def test_tag_mode_has_no_effect_without_tags(self):
        for mode in (TAG_MODE_ANY, TAG_MODE_ALL):
            with self.subTest(mode=mode):
                self.assertEqual(self.names(tag_mode=mode), self.ALL_NAMES)

    def test_filters_combine_with_and(self):
        cases = [
            ({"q": "kettle", "category": self.kitchen}, ["Kettle"]),
            ({"q": "kettle", "category": self.garden}, []),
            (
                {
                    "category": self.kitchen,
                    "tags": [self.gift, self.sale],
                    "tag_mode": TAG_MODE_ALL,
                },
                ["Kettle"],
            ),
            (
                {
                    "category": self.kitchen,
                    "tags": [self.gift, self.sale],
                    "tag_mode": TAG_MODE_ANY,
                },
                ["Kettle", "Pan", "Toaster"],
            ),
            (
                {"q": "garden", "category": self.garden, "tags": [self.new]},
                ["Hose"],
            ),
            ({"q": "bread", "tags": [self.sale], "tag_mode": TAG_MODE_ANY}, []),
        ]
        for filters, expected in cases:
            with self.subTest(filters=filters):
                self.assertEqual(self.names(**filters), expected)

    def test_results_keep_the_default_ordering(self):
        qs = filter_products(
            Product.objects.all(),
            {"tags": [self.gift, self.sale], "tag_mode": TAG_MODE_ANY},
        )
        self.assertEqual(list(qs), sorted(qs, key=lambda p: (p.name, p.pk)))


class ProductFilterFormTests(FilterTestCase):
    def test_empty_submission_is_valid_with_defaults(self):
        form = ProductFilterForm({})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["q"], "")
        self.assertIsNone(form.cleaned_data["category"])
        self.assertEqual(list(form.cleaned_data["tags"]), [])
        self.assertEqual(form.cleaned_data["tag_mode"], TAG_MODE_ANY)

    def test_unbound_form_defaults_to_any_mode(self):
        self.assertEqual(ProductFilterForm().fields["tag_mode"].initial, TAG_MODE_ANY)

    def test_search_text_is_trimmed(self):
        form = ProductFilterForm({"q": "  kettle  "})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["q"], "kettle")

    def test_blank_search_means_no_search(self):
        form = ProductFilterForm({"q": "   "})
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["q"], "")
        names = [
            p.name for p in filter_products(Product.objects.all(), form.cleaned_data)
        ]
        self.assertEqual(len(names), Product.objects.count())

    def test_tag_mode_accepts_supported_values(self):
        for mode in (TAG_MODE_ANY, TAG_MODE_ALL):
            with self.subTest(mode=mode):
                form = ProductFilterForm({"tag_mode": mode})
                self.assertTrue(form.is_valid())
                self.assertEqual(form.cleaned_data["tag_mode"], mode)

    def test_missing_or_blank_tag_mode_defaults_to_any(self):
        for data in ({}, {"tag_mode": ""}):
            with self.subTest(data=data):
                form = ProductFilterForm(data)
                self.assertTrue(form.is_valid())
                self.assertEqual(form.cleaned_data["tag_mode"], TAG_MODE_ANY)

    def test_unsupported_tag_mode_is_rejected(self):
        form = ProductFilterForm({"tag_mode": "some"})
        self.assertFalse(form.is_valid())
        self.assertIn("tag_mode", form.errors)

    def test_unknown_or_malformed_category_is_rejected(self):
        for value in ("99999", "abc", "-1"):
            with self.subTest(category=value):
                form = ProductFilterForm({"category": value})
                self.assertFalse(form.is_valid())
                self.assertIn("category", form.errors)

    def test_unknown_or_malformed_tag_is_rejected(self):
        for bad in ("99999", "abc"):
            with self.subTest(tag=bad):
                form = ProductFilterForm(QueryDict(f"tags={self.gift.pk}&tags={bad}"))
                self.assertFalse(form.is_valid())
                self.assertIn("tags", form.errors)

    def test_choices_are_ordered_by_name(self):
        form = ProductFilterForm()
        self.assertEqual(
            [c.name for c in form.fields["category"].queryset], ["Garden", "Kitchen"]
        )
        self.assertEqual(
            [t.name for t in form.fields["tags"].queryset],
            ["gift", "handmade", "new", "popular", "sale"],
        )

    def test_query_string_with_repeated_tags_drives_the_filter(self):
        query = f"q=&category=&tags={self.gift.pk}&tags={self.sale.pk}&tag_mode=all"
        form = ProductFilterForm(QueryDict(query))
        self.assertTrue(form.is_valid())
        names = [
            p.name for p in filter_products(Product.objects.all(), form.cleaned_data)
        ]
        self.assertEqual(names, ["Hose", "Kettle"])

    def test_query_string_combining_every_filter(self):
        query = (
            f"q=boils&category={self.kitchen.pk}"
            f"&tags={self.gift.pk}&tags={self.sale.pk}&tag_mode=any"
        )
        form = ProductFilterForm(QueryDict(query))
        self.assertTrue(form.is_valid())
        names = [
            p.name for p in filter_products(Product.objects.all(), form.cleaned_data)
        ]
        self.assertEqual(names, ["Kettle"])

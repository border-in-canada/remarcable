from django import forms

from .models import Category, Tag
from .querysets import TAG_MODE_ALL, TAG_MODE_ANY


class ProductFilterForm(forms.Form):
    q = forms.CharField(label="Search descriptions", required=False)
    # Every category and tag is listed, which is fine for a small catalog. If
    # the lists grow large, switch to type-ahead lookups: a long dropdown or
    # checkbox list becomes a usability problem before a performance one.
    #
    # These choices are not cached because they are two small indexed queries.
    # Consider caching only if profiling shows they matter, for example with a
    # remote database under heavy traffic. Use a shared cache and clear it when a
    # category or tag is added, renamed or deleted, including bulk changes, which
    # skip Django signals.
    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        empty_label="All categories",
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )
    tag_mode = forms.ChoiceField(
        label="Match",
        choices=[
            (TAG_MODE_ANY, "Any selected tag"),
            (TAG_MODE_ALL, "All selected tags"),
        ],
        initial=TAG_MODE_ANY,
        required=False,
        widget=forms.RadioSelect,
    )

    def clean_tag_mode(self):
        # Fallback for edited or bookmarked URLs that may omit the mode
        return self.cleaned_data["tag_mode"] or TAG_MODE_ANY

from django import forms

from .models import Category, Tag
from .querysets import TAG_MODE_ALL, TAG_MODE_ANY


class ProductFilterForm(forms.Form):
    q = forms.CharField(label="Search descriptions", required=False)
    # Lists every category and tag, which suits a small catalog. At scale, use
    # type-ahead lookups instead of a full dropdown and checkbox list.
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

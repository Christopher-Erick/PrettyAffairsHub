from django import forms

from .models import Review


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ("author_name", "rating", "title", "body")
        widgets = {
            "author_name": forms.TextInput(attrs={"class": "field"}),
            "rating": forms.NumberInput(attrs={"class": "field", "min": 1, "max": 5}),
            "title": forms.TextInput(attrs={"class": "field"}),
            "body": forms.Textarea(attrs={"class": "field", "rows": 4}),
        }

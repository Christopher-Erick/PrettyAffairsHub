from django import forms
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth.models import User

from .models import Address, CustomerProfile
from .roles import assign_client_role


class RegisterForm(UserCreationForm):
    email = forms.EmailField(required=True)
    first_name = forms.CharField(required=False)
    last_name = forms.CharField(required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"]
        user.first_name = self.cleaned_data.get("first_name", "")
        user.last_name = self.cleaned_data.get("last_name", "")
        user.is_staff = False
        user.is_superuser = False
        if commit:
            user.save()
            if hasattr(self, "save_m2m"):
                self.save_m2m()
            assign_client_role(user)
        return user


class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={"class": "field", "autocomplete": "username"}))
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={"class": "field", "autocomplete": "current-password"})
    )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs={"class": "field"}))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs={"class": "field"}))

    class Meta:
        model = CustomerProfile
        fields = ("phone",)
        widgets = {"phone": forms.TextInput(attrs={"class": "field"})}


class AddressForm(forms.ModelForm):
    class Meta:
        model = Address
        fields = (
            "full_name",
            "phone",
            "line1",
            "line2",
            "city",
            "county",
            "postal_code",
            "country",
            "is_default",
        )
        widgets = {
            "full_name": forms.TextInput(attrs={"class": "field"}),
            "phone": forms.TextInput(attrs={"class": "field"}),
            "line1": forms.TextInput(attrs={"class": "field"}),
            "line2": forms.TextInput(attrs={"class": "field"}),
            "city": forms.TextInput(attrs={"class": "field"}),
            "county": forms.TextInput(attrs={"class": "field"}),
            "postal_code": forms.TextInput(attrs={"class": "field"}),
            "country": forms.TextInput(attrs={"class": "field"}),
        }

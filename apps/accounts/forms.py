from django import forms
from django.contrib.auth.forms import (
    AuthenticationForm,
    PasswordResetForm,
    SetPasswordForm,
    UserCreationForm,
)
from django.contrib.auth.models import User

from .models import Address, CustomerProfile
from .roles import assign_client_role, is_store_admin

_FIELD = {"class": "field"}


class RegisterForm(UserCreationForm):
    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(attrs={**_FIELD, "autocomplete": "email"}),
    )
    first_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={**_FIELD, "autocomplete": "given-name"}),
    )
    last_name = forms.CharField(
        required=False,
        widget=forms.TextInput(attrs={**_FIELD, "autocomplete": "family-name"}),
    )

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].widget.attrs.update({**_FIELD, "autocomplete": "username"})
        self.fields["password1"].widget.attrs.update({**_FIELD, "autocomplete": "new-password"})
        self.fields["password2"].widget.attrs.update({**_FIELD, "autocomplete": "new-password"})

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
    """Clients sign in with email; store admins sign in with username."""

    username = forms.CharField(
        label="Email",
        widget=forms.TextInput(
            attrs={
                **_FIELD,
                "autocomplete": "username",
                "placeholder": "you@example.com",
                "inputmode": "email",
            }
        ),
    )
    password = forms.CharField(
        label="Password",
        widget=forms.PasswordInput(attrs={**_FIELD, "autocomplete": "current-password"}),
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Customers use email. Staff use their username."

    def clean(self):
        login_id = (self.cleaned_data.get("username") or "").strip()
        password = self.cleaned_data.get("password")
        if login_id and password:
            self.cleaned_data["username"] = self._resolve_auth_username(login_id)
        return super().clean()

    def _resolve_auth_username(self, login_id: str) -> str:
        if "@" in login_id:
            matches = list(User.objects.filter(email__iexact=login_id, is_active=True))
            clients = [user for user in matches if not is_store_admin(user)]
            staff = [user for user in matches if is_store_admin(user)]
            if clients:
                return clients[0].username
            if staff:
                raise forms.ValidationError(
                    "Staff accounts sign in with username, not email.",
                    code="staff_use_username",
                )
            return login_id

        user = User.objects.filter(username__iexact=login_id, is_active=True).first()
        if user and not is_store_admin(user):
            raise forms.ValidationError(
                "Please sign in with your email address.",
                code="client_use_email",
            )
        if user:
            return user.username
        return login_id


class StyledPasswordResetForm(PasswordResetForm):
    """Public reset is for client shoppers only — never staff / store admins."""

    email = forms.EmailField(
        label="Email",
        max_length=254,
        widget=forms.EmailInput(
            attrs={
                **_FIELD,
                "autocomplete": "email",
                "placeholder": "you@example.com",
            }
        ),
    )

    def get_users(self, email):
        for user in super().get_users(email):
            if is_store_admin(user):
                continue
            yield user


class StyledSetPasswordForm(SetPasswordForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["new_password1"].widget.attrs.update(
            {**_FIELD, "autocomplete": "new-password"}
        )
        self.fields["new_password2"].widget.attrs.update(
            {**_FIELD, "autocomplete": "new-password"}
        )


class ProfileForm(forms.ModelForm):
    first_name = forms.CharField(required=False, widget=forms.TextInput(attrs=_FIELD))
    last_name = forms.CharField(required=False, widget=forms.TextInput(attrs=_FIELD))
    email = forms.EmailField(required=True, widget=forms.EmailInput(attrs=_FIELD))

    class Meta:
        model = CustomerProfile
        fields = ("phone",)
        widgets = {"phone": forms.TextInput(attrs={**_FIELD, "autocomplete": "tel"})}


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
            "full_name": forms.TextInput(attrs=_FIELD),
            "phone": forms.TextInput(attrs=_FIELD),
            "line1": forms.TextInput(attrs=_FIELD),
            "line2": forms.TextInput(attrs=_FIELD),
            "city": forms.TextInput(attrs=_FIELD),
            "county": forms.TextInput(attrs=_FIELD),
            "postal_code": forms.TextInput(attrs=_FIELD),
            "country": forms.TextInput(attrs=_FIELD),
        }

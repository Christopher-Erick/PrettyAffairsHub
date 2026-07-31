from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import LoginView, LogoutView
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse_lazy
from django.views.decorators.http import require_POST
from django.views.generic import CreateView

from apps.accounts.forms import AddressForm, ProfileForm, RegisterForm
from apps.accounts.models import Address, CustomerProfile
from apps.accounts.roles import is_store_admin
from apps.accounts.services import get_or_create_wishlist, toggle_wishlist
from apps.catalog.models import Product
from apps.orders.models import Order


class RegisterView(CreateView):
    form_class = RegisterForm
    template_name = "accounts/register.html"
    success_url = reverse_lazy("accounts:profile")

    def form_valid(self, form):
        response = super().form_valid(form)
        CustomerProfile.objects.get_or_create(user=self.object)
        login(self.request, self.object)
        messages.success(self.request, "Welcome to Pretty Affairs Hub.")
        return response


class UserLoginView(LoginView):
    template_name = "accounts/login.html"
    redirect_authenticated_user = True

    def form_valid(self, form):
        response = super().form_valid(form)
        if is_store_admin(self.request.user):
            messages.info(
                self.request,
                "Welcome back. Store admin tools are available from your account.",
            )
        return response

    def get_success_url(self):
        # Clients and admins both land on Account; admins see the Store admin CTA there.
        return self.get_redirect_url() or reverse_lazy("accounts:profile")


class UserLogoutView(LogoutView):
    next_page = reverse_lazy("content:home")


@login_required
def profile(request):
    profile_obj, _ = CustomerProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = ProfileForm(request.POST, instance=profile_obj)
        if form.is_valid():
            form.save()
            request.user.first_name = form.cleaned_data.get("first_name", "")
            request.user.last_name = form.cleaned_data.get("last_name", "")
            request.user.email = form.cleaned_data["email"]
            request.user.save()
            messages.success(request, "Profile updated.")
            return redirect("accounts:profile")
    else:
        form = ProfileForm(
            instance=profile_obj,
            initial={
                "first_name": request.user.first_name,
                "last_name": request.user.last_name,
                "email": request.user.email,
            },
        )
    orders = Order.objects.filter(user=request.user)[:10]
    return render(
        request,
        "accounts/profile.html",
        {
            "form": form,
            "orders": orders,
            "addresses": request.user.addresses.all(),
            "is_store_admin": is_store_admin(request.user),
        },
    )


@login_required
def address_create(request):
    form = AddressForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        address = form.save(commit=False)
        address.user = request.user
        if address.is_default:
            Address.objects.filter(user=request.user).update(is_default=False)
        address.save()
        messages.success(request, "Address saved.")
        return redirect("accounts:profile")
    return render(request, "accounts/address_form.html", {"form": form})


@login_required
def wishlist(request):
    wl = get_or_create_wishlist(request.user)
    return render(request, "accounts/wishlist.html", {"products": wl.products.published()})


@login_required
@require_POST
def wishlist_toggle(request, slug):
    product = get_object_or_404(Product, slug=slug, is_active=True)
    added = toggle_wishlist(request.user, product)
    messages.success(request, "Added to wishlist." if added else "Removed from wishlist.")
    next_url = request.POST.get("next") or product.get_absolute_url()
    return redirect(next_url)

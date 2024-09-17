from allauth.account.adapter import get_adapter
from allauth.account.forms import SignupForm
from allauth.account.utils import setup_user_email
from django import forms
from django.core.validators import RegexValidator

from .models import User


class CustomSignupForm(SignupForm):
    phone_number = forms.CharField(max_length=11, validators=[RegexValidator(r'^\d{11}$')], label='Phone Number', required=True, widget=forms.TextInput(attrs={'placeholder': 'شماره همراه'}))
    first_name = forms.CharField(max_length=60, label='First Name', required=True, widget=forms.TextInput(attrs={'placeholder': 'نام'}))
    last_name = forms.CharField(max_length=60, label='Last Name', required=True, widget=forms.TextInput(attrs={'placeholder': 'نام خانوادگی'}))

    def save(self, request):
        adapter = get_adapter(request)
        user = adapter.new_user(request)
        adapter.save_user(request, user, self)
        self.custom_signup(request, user)
        setup_user_email(request, user, [])
        user.phone_number = self.cleaned_data['phone_number']
        user.first_name = self.cleaned_data['first_name']
        user.last_name = self.cleaned_data['last_name']
        user.save()
        return user


class UserAddress(forms.ModelForm):
    class Meta:
        model = User
        fields = ('first_name', 'last_name', 'state', 'city',
                  'address', 'zipcode', 'phone_number')
        widgets = {
            'first_name': forms.TextInput(attrs={'placeholder': 'نام'}),
            'last_name': forms.TextInput(attrs={'placeholder': 'نام خانوادگی'}),
            'state': forms.Select(attrs={'placeholder': 'استان'}),
            'city': forms.Select(attrs={'placeholder': 'شهر'}),
            'address': forms.TextInput(attrs={'placeholder': 'آدرس'}),
            'zipcode': forms.TextInput(attrs={'placeholder': 'کد پستی'}),
            'phone_number': forms.TextInput(attrs={'placeholder': 'شماره همراه'}),
        }

    def clean(self):
        super(UserAddress, self).clean()
        zipcode = self.cleaned_data.get('zipcode')
        phone_number = self.cleaned_data.get('phone_number')
        if len(zipcode) < 10:
            self._errors['zipcode'] = self.error_class(
                ['کد پستی باید 10 رقمی باشد'])
        if len(phone_number) < 11:
            self._errors['phone_number'] = self.error_class(
                ['شماره همراه باید 11 رقمی باشد'])
        return self.cleaned_data


class SellerRequest(forms.ModelForm):
    class Meta:
        model = User
        fields = ('seller_title', 'national_card_image', 'shaba_number', 'phone_number', 'slug', 'profile_image', 'commitment_to_send', 'request_seller')


class SellerEdit(forms.ModelForm):
    class Meta:
        model = User
        fields = ('seller_title', 'phone_number', 'slug', 'profile_image')

    # def clean(self):
    #     super(SellerRequest, self).clean()
    #     zipcode = self.cleaned_data.get('zipcode')
    #     phone_number = self.cleaned_data.get('phone_number')
    #     if len(zipcode) < 10:
    #         self._errors['zipcode'] = self.error_class(
    #             ['کد پستی باید 10 رقمی باشد'])
    #     if len(phone_number) < 11:
    #         self._errors['phone_number'] = self.error_class(
    #             ['شماره همراه باید 11 رقمی باشد'])
    #     return self.cleaned_data

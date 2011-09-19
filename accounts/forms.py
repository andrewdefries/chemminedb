from django import forms
from django.contrib.auth.models import User
from django.forms.util import ErrorList

class SignUpForm(forms.Form):
	first = forms.CharField(max_length=30, required=True, label="First Name")
	last = forms.CharField(max_length=30, required=True, label="Last Name")
	email = forms.EmailField(max_length=75, required=True, label='E-mail')
	password = forms.CharField(widget=forms.PasswordInput, max_length=250,
								required=True)
	confirm  = forms.CharField(widget=forms.PasswordInput, max_length=250,
								required=True)
	institute = forms.CharField(max_length=250, required=True)

	def clean_email(self):
		email = self.cleaned_data['email']
		if User.objects.filter(email=email).count():
			raise forms.ValidationError("E-mail address already registered")
		return self.cleaned_data['email']

	def clean(self):
		if self.cleaned_data['password'] != self.cleaned_data['confirm']:
			self._errors['password'] = ErrorList(["Passwords do not match"])
			raise forms.ValidationError("Passwords do not match")
		return self.cleaned_data

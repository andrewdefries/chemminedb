from django import forms
from cmplatform import models

class UserObjectForm(forms.Form):
	name = forms.CharField(max_length=250, required=True)
	pure_text = forms.BooleanField(label="Pure Text Object",
				required=False, initial=True)
	override = forms.BooleanField(label="Override Existing Object",
				required=False, initial=True)
	content = forms.CharField(widget=forms.Textarea,
				help_text="Pure Text or JSON-encoded object")

	def clean_name(self):
		if '|' in self.cleaned_data['name']:
			raise forms.ValidationError('"|" is not allowed in object name')
		return self.cleaned_data['name']

	def clean(self):
		if not self.cleaned_data.get('pure_text'):
			json_data = unicode.encode(
					self.cleaned_data['content'], 'utf-8')
			self.cleaned_data['content'] = json_data
			try:
				models.JSONData(json_data)
			except:
				raise forms.ValidationError('JSON content is malformed')
		return self.cleaned_data

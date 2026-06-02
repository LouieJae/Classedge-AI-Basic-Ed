from accounts.models import Certificate
from django import forms

class CertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['profiles', 'title', 'file', 'is_featured']
        widgets = {
            'profiles': forms.SelectMultiple(attrs={
                'class': 'cert-recipients-select',
                'data-placeholder': 'Search and pick recipients…',
            }),
            'title': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Certificate title'}),
        }

class BulkCertificateForm(forms.ModelForm):
    class Meta:
        model = Certificate
        fields = ['title', 'file', 'is_featured']
        widgets = {
            'title': forms.TextInput(attrs={'class': 'form-control' }),
        }
        
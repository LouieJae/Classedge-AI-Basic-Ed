from django import forms
from course.models import Term
from subject.models import Subject


class ParticipationForm(forms.Form):
    term = forms.ModelChoiceField(
        queryset=Term.objects.all(),
        label="Select Term",                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                                      
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    subject = forms.ModelChoiceField(
        queryset=Subject.objects.all(),
        label="Select Course",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    max_score = forms.DecimalField(
        max_digits=5, 
        decimal_places=2, 
        label="Max Score", 
        initial=100,
        widget=forms.NumberInput(attrs={'class': 'form-control'})
    )

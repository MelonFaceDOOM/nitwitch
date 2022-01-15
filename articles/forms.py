from django import forms
from .models import *


class ArticleImageForm(forms.ModelForm):
    image = forms.ImageField(label='Image')

    class Meta:
        model = ArticleImage
        fields = ('image',)

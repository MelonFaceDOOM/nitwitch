from django.contrib.auth.forms import UserCreationForm, UserChangeForm
from .models import CustomUser


class CustomUserCreationForm(UserCreationForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')

class CustomUserChangeForm(UserChangeForm):
    class Meta:
        model = CustomUser
        fields = ('username', 'email')
        

## USER GROUP PERMISSION MODEL

# this will let you assign a defualt role to new users
# class SignupForm(forms.Form):
    # pass

    # def signup(self, request, user):
        # default_group = Group.objects.get('Default')
        # user.groups.add(default_group)
        # user.save()

# also need to put this in settings.py
# ACCOUNT_SIGNUP_FORM_CLASS = 'accounts.forms.SignupForm'        
        
# Defining Groups
# default_group, created = Group.objects.get_or_create(name='Default')
# content_type = ContentType.objects.get_for_model(Article)
# permission = Permission.objects.get(
        # codename='view_article',
        # content_type=content_type,
    # )
# default_group.permissions.add(permission)
# # 'articles.change_article', 'articles.add_article', 'articles.delete_article'
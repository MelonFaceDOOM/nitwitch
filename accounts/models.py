from django.contrib.auth.models import AbstractUser
from django.db import models


class CustomUser(AbstractUser):

    def __str__(self):
        return self.email


class BannedIP(models.Model):
    ip_address = models.GenericIPAddressField(unique=True)
    date_entered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.ip_address


def is_ip_banned(ip_address):
    return BannedIP.objects.filter(ip_address=ip_address).exists()

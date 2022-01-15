from django.db import models
import datetime
from static.markup import melon_markup
import secrets


class Article(models.Model):
    title = models.CharField(max_length=200, unique=True)
    author = models.CharField(max_length=200)
    article_text = models.CharField(max_length=500000)
    article_text_formatted = models.CharField(max_length=500000)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    edit_date = models.DateTimeField('date published', auto_now=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(check=~models.Q(title=""), name="non_empty_title")
        ]

    @classmethod
    def create_placeholder(cls):
        title = secrets.token_hex(16)
        placeholder = cls(title=title)
        placeholder.save()
        return placeholder

    def apply_markup(self):
        self.article_text_formatted = melon_markup.parse(self.article_text)
        self.save()

### This no longer needs to happen automatically. Instead, a method is called after the article_text is added.
### leaving it here in case i want to see execute_after_save example in the future
# from django.dispatch import receiver
# @receiver(models.signals.post_save, sender=Article)
# def execute_after_save(sender, instance, created, *args, **kwargs):
#     if created:
#         instance.article_text_formatted = melon_markup.parse(instance.article_text)
#         instance.save()


class ArticleImage(models.Model):
    article = models.ForeignKey(Article, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(upload_to='article_images/')

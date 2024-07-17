from django.db import models
import datetime
from markup import melon_markup
import secrets


class Article(models.Model):
    title = models.CharField(max_length=200, unique=True)
    author = models.CharField(max_length=200)
    description = models.CharField(max_length=200, blank=True, default="")
    article_text = models.CharField(max_length=500000)
    article_text_formatted = models.CharField(max_length=500000)
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    edit_date = models.DateTimeField('date edited', auto_now=True)
    view_count = models.IntegerField(default=0)

    class Meta:
        constraints = [
            models.CheckConstraint(check=~models.Q(title=""), name="non_empty_title")
        ]

    @classmethod
    def create_placeholder(cls):
        title = secrets.token_hex(16)
        article_text = ":)"
        placeholder = cls(title=title, article_text=article_text)
        placeholder.save()
        return placeholder

    def apply_markup(self):
        # this only occurs when it is directly called. Therefore if you want to upload straight html, you
        # can just put it in the field article_text_formatted and leave article_text blank
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


class ArticleComment(models.Model):
    article = models.ForeignKey(Article, related_name='comments', on_delete=models.CASCADE)
    date_entered = models.DateTimeField(auto_now_add=True)
    comment_text = models.CharField(max_length=400)
    ambiguity = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField()

    def get_comment_type(self):
        return self.__class__.__name__


class ArticleCommentAmbiguityVote(models.Model):
    VOTE_CHOICES = (
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    )
    article_comment = models.ForeignKey(ArticleComment, related_name='ambiguity_votes', on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    ip_address = models.GenericIPAddressField()
    date_entered = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure that the combination of ip_address and image is unique
        unique_together = ('ip_address', 'article_comment')

    def delete(self, *args, **kwargs):
        parent_object = self.article_comment
        if self.vote_type == 'increase':
            parent_object.ambiguity -= 1
        elif self.vote_type == 'decrease':
            parent_object.ambiguity += 1
        parent_object.save()
        super().delete(*args, **kwargs)

    @property
    def ambiguity_object(self):
        # this makes it so various funcs can refer to ambiguity_object for all vote classes
        return self.article_comment

    @ambiguity_object.setter
    def ambiguity_object(self, value):
        self.article_comment = value

    @classmethod
    def get_by_ambiguity_object(cls, ambiguity_object):
        try:
            return cls.objects.get(article_comment=ambiguity_object)
        except:
            return None

    @classmethod
    def create_with_ambiguity_object(cls, ip_address, ambiguity_object, vote_type):
        return cls.objects.create(ip_address=ip_address, article_comment=ambiguity_object, vote_type=vote_type)

    def get_vote_type(self):
        return self.__class__.__name__

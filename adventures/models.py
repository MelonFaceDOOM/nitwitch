from django.db import models


class Adventure(models.Model):
    title = models.CharField(max_length=200, unique=True)
    author = models.CharField(max_length=200)
    description = models.TextField(blank=True, default="")
    pub_date = models.DateTimeField('date published', auto_now_add=True)
    edit_date = models.DateTimeField('date edited', auto_now=True)
    view_count = models.IntegerField(default=0)
    category = models.CharField(max_length=3)
    category_index = models.PositiveIntegerField()

    def display_name(self):
        return f"({self.category}-{self.category_index}) {self.title}"

    def __str__(self):
        return self.display_name()

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=['category', 'category_index'], name='unique_category_index')
        ]

    def save(self, *args, **kwargs):
        if not self.pk:  # Only set category_index if it's a new object
            max_index = Adventure.objects.filter(category=self.category).aggregate(models.Max('category_index'))[
                'category_index__max']
            self.category_index = 1 if max_index is None else max_index + 1
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.category}-{self.category_index}: {self.title}"


class GameCard(models.Model):
    adventure = models.ForeignKey(Adventure, related_name='game_cards', on_delete=models.CASCADE)
    card_id = models.CharField(max_length=255)
    card_text = models.TextField()


class CardOption(models.Model):
    parent_card = models.ForeignKey(GameCard, related_name='card_options', on_delete=models.CASCADE)
    linked_card_id = models.CharField(max_length=255)  # easier to just store text rather than link to the object which might not exist yet
    option_text = models.CharField(max_length=5000)

from django.db import models


def _short_id(snowflake) -> str:
    s = str(snowflake)
    return f"…{s[-4:]}" if len(s) > 4 else s


class Guild(models.Model):
    id = models.BigIntegerField(primary_key=True)
    date = models.DateTimeField(blank=True, null=True)
    # Bot-synced cache columns (nullable until the Discord bot fills them).
    name = models.CharField(max_length=128, blank=True, null=True)
    icon_url = models.TextField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'guilds'

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.name:
            return self.name
        return f"Guild {_short_id(self.id)}"

    @property
    def display_id(self):
        return _short_id(self.id)


class DiscordUser(models.Model):
    id = models.BigIntegerField(primary_key=True)
    date = models.DateTimeField(blank=True, null=True)
    # Bot-synced cache columns (nullable until the Discord bot fills them).
    username = models.CharField(max_length=64, blank=True, null=True)
    global_name = models.CharField(max_length=64, blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.display_name

    @property
    def display_name(self):
        if self.global_name:
            return self.global_name
        if self.username:
            return self.username
        # Full snowflake when names are not cached yet (fits list/detail columns).
        return str(self.id)

    @property
    def display_id(self):
        return _short_id(self.id)


class Movie(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        DiscordUser, on_delete=models.DO_NOTHING, db_column='user_id',
        related_name='movies',
    )
    guild = models.ForeignKey(
        Guild, on_delete=models.DO_NOTHING, db_column='guild_id',
        related_name='movies',
    )
    title = models.CharField(max_length=256)
    date_suggested = models.DateTimeField(blank=True, null=True)
    date_watched = models.DateTimeField(blank=True, null=True)
    watched = models.IntegerField(default=0)

    class Meta:
        managed = False
        db_table = 'movies'

    def __str__(self):
        return self.title

    @property
    def is_watched(self):
        return bool(self.watched)


class Endorsement(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        DiscordUser, on_delete=models.DO_NOTHING, db_column='user_id',
        related_name='endorsements',
    )
    guild = models.ForeignKey(
        Guild, on_delete=models.DO_NOTHING, db_column='guild_id',
        related_name='endorsements',
    )
    date = models.DateTimeField(blank=True, null=True)
    movie = models.ForeignKey(
        Movie, on_delete=models.DO_NOTHING, db_column='movie_id',
        related_name='endorsements',
    )

    class Meta:
        managed = False
        db_table = 'endorsements'


class Rating(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        DiscordUser, on_delete=models.DO_NOTHING, db_column='user_id',
        related_name='ratings',
    )
    guild = models.ForeignKey(
        Guild, on_delete=models.DO_NOTHING, db_column='guild_id',
        related_name='ratings',
    )
    date = models.DateTimeField(blank=True, null=True)
    movie = models.ForeignKey(
        Movie, on_delete=models.DO_NOTHING, db_column='movie_id',
        related_name='ratings',
    )
    rating = models.FloatField()

    class Meta:
        managed = False
        db_table = 'ratings'


class Review(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(
        DiscordUser, on_delete=models.DO_NOTHING, db_column='user_id',
        related_name='reviews',
    )
    guild = models.ForeignKey(
        Guild, on_delete=models.DO_NOTHING, db_column='guild_id',
        related_name='reviews',
    )
    date = models.DateTimeField(blank=True, null=True)
    movie = models.ForeignKey(
        Movie, on_delete=models.DO_NOTHING, db_column='movie_id',
        related_name='reviews',
    )
    review_text = models.TextField()

    class Meta:
        managed = False
        db_table = 'reviews'

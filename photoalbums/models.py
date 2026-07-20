from django.db import models
from PIL import Image, ImageOps
from io import BytesIO
from django.core.files import File
import secrets


class PhotoAlbum(models.Model):
    title = models.CharField(max_length=200, unique=True)
    author = models.CharField(max_length=200)
    description = models.CharField(max_length=200)
    pub_date = models.DateTimeField("date published", auto_now_add=True)

    class Meta:
        constraints = [
            models.CheckConstraint(check=~models.Q(title=""), name="non_empty_title_photoalbum")
        ]

    @classmethod
    def create_placeholder(cls):
        title = secrets.token_hex(16)
        placeholder = cls(title=title)
        placeholder.save()
        return placeholder

    def __str__(self):
        return self.description


class PhotoAlbumImage(models.Model):
    album = models.ForeignKey(PhotoAlbum, related_name='images', on_delete=models.CASCADE)
    image = models.FileField(upload_to='photo_albums/')
    thumbnail = models.FileField(upload_to='photo_albums/', blank=True, null=True)
    description = models.CharField(max_length=4000)
    date_uploaded = models.DateTimeField(auto_now_add=True)
    ambiguity = models.IntegerField(default=0)

    def __str__(self):
        return self.description

    def save(self, *args, **kwargs):
        super(PhotoAlbumImage, self).save(*args, **kwargs)
        if self.image:
            self.resize_image()

    def resize_image(self):
        # Apply EXIF orientation so phone photos aren't sideways in thumbs
        # while browsers still show the full image upright.
        self.image.open()
        image = ImageOps.exif_transpose(Image.open(self.image))

        # Define the maximum size for the smaller image
        max_size = (256, 256)

        # Preserve aspect ratio while resizing
        image.thumbnail(max_size, resample=Image.LANCZOS)

        # Save the resized image to the image_small field
        temp_io = BytesIO()
        image.save(temp_io, format='PNG')  # this is like saving a file but to the temp_io variable
        temp_io.seek(0)
        thumbnail_name = f'thumbnail_{self.image.name}'
        self.thumbnail.save(thumbnail_name, File(temp_io), save=False)  # save the thumbnail image to db
        super(PhotoAlbumImage, self).save()  # save the image itself now that the thumbnail field is populated


class ImageComment(models.Model):
    image = models.ForeignKey(PhotoAlbumImage, related_name='comments', on_delete=models.CASCADE)
    date_entered = models.DateTimeField(auto_now_add=True)
    comment_text = models.CharField(max_length=400)
    ambiguity = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField()

    def get_comment_type(self):
        return self.__class__.__name__


class PhotoAlbumComment(models.Model):
    photoalbum = models.ForeignKey(PhotoAlbum, related_name='comments', on_delete=models.CASCADE)
    date_entered = models.DateTimeField(auto_now_add=True)
    comment_text = models.CharField(max_length=400)
    ambiguity = models.IntegerField(default=0)
    ip_address = models.GenericIPAddressField()

    def get_comment_type(self):
        return self.__class__.__name__


class ImageAmbiguityVote(models.Model):
    VOTE_CHOICES = (
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    )
    image = models.ForeignKey(PhotoAlbumImage, related_name='ambiguity_votes', on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    ip_address = models.GenericIPAddressField()
    date_entered = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure that the combination of ip_address and image is unique
        unique_together = ('ip_address', 'image')

    def delete(self, *args, **kwargs):
        parent_object = self.image
        if self.vote_type == 'increase':
            parent_object.ambiguity -= 1
        elif self.vote_type == 'decrease':
            parent_object.ambiguity += 1
        parent_object.save()
        super().delete(*args, **kwargs)

    @property
    def ambiguity_object(self):
        # this makes it so various funcs can refer to ambiguity_object for all vote classes
        return self.image

    @ambiguity_object.setter
    def ambiguity_object(self, value):
        self.image = value

    @classmethod
    def get_by_ambiguity_object(cls, ambiguity_object):
        try:
            return cls.objects.get(image=ambiguity_object)
        except:
            return None

    @classmethod
    def create_with_ambiguity_object(cls, ip_address, ambiguity_object, vote_type):
        return cls.objects.create(ip_address=ip_address, image=ambiguity_object, vote_type=vote_type)

    def get_vote_type(self):
        return self.__class__.__name__


class ImageCommentAmbiguityVote(models.Model):
    VOTE_CHOICES = (
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    )
    image_comment = models.ForeignKey(ImageComment, related_name='ambiguity_votes', on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    ip_address = models.GenericIPAddressField()
    date_entered = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure that the combination of ip_address and image is unique
        unique_together = ('ip_address', 'image_comment')

    def delete(self, *args, **kwargs):
        parent_object = self.image_comment
        if self.vote_type == 'increase':
            parent_object.ambiguity -= 1
        elif self.vote_type == 'decrease':
            parent_object.ambiguity += 1
        parent_object.save()
        super().delete(*args, **kwargs)

    @property
    def ambiguity_object(self):
        return self.image_comment

    @ambiguity_object.setter
    def ambiguity_object(self, value):
        self.image_comment = value

    @classmethod
    def get_by_ambiguity_object(cls, ambiguity_object):
        try:
            return cls.objects.get(image_comment=ambiguity_object)
        except:
            return None

    @classmethod
    def create_with_ambiguity_object(cls, ip_address, ambiguity_object, vote_type):
        return cls.objects.create(ip_address=ip_address, image_comment=ambiguity_object, vote_type=vote_type)

    def get_vote_type(self):
        return self.__class__.__name__


class PhotoAlbumCommentAmbiguityVote(models.Model):
    VOTE_CHOICES = (
        ('increase', 'Increase'),
        ('decrease', 'Decrease'),
    )
    photoalbum_comment = models.ForeignKey(PhotoAlbumComment, related_name='ambiguity_votes', on_delete=models.CASCADE)
    vote_type = models.CharField(max_length=10, choices=VOTE_CHOICES)
    ip_address = models.GenericIPAddressField()
    date_entered = models.DateTimeField(auto_now_add=True)

    class Meta:
        # Ensure that the combination of ip_address and image is unique
        unique_together = ('ip_address', 'photoalbum_comment')

    def delete(self, *args, **kwargs):
        parent_object = self.photoalbum_comment
        if self.vote_type == 'increase':
            parent_object.ambiguity -= 1
        elif self.vote_type == 'decrease':
            parent_object.ambiguity += 1
        parent_object.save()
        super().delete(*args, **kwargs)

    @property
    def ambiguity_object(self):
        return self.photoalbum_comment

    @ambiguity_object.setter
    def ambiguity_object(self, value):
        self.photoalbum_comment = value

    @classmethod
    def get_by_ambiguity_object(cls, ambiguity_object):
        try:
            return cls.objects.get(photoalbum_comment=ambiguity_object)
        except:
            return None

    @classmethod
    def create_with_ambiguity_object(cls, ip_address, ambiguity_object, vote_type):
        return cls.objects.create(ip_address=ip_address, photoalbum_comment=ambiguity_object, vote_type=vote_type)

    def get_vote_type(self):
        return self.__class__.__name__
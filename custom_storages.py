import config
from storages.backends.s3boto3 import S3Boto3Storage

class StaticStorage(S3Boto3Storage):
    location = config.STATICFILES_LOCATION

class MediaStorage(S3Boto3Storage):
    location = config.MEDIAFILES_LOCATION


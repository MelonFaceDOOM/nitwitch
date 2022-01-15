from django.db import models
from django.utils.timezone import make_aware
import datetime


def current_time_with_tz():
    return make_aware(datetime.datetime.now())


class Event(models.Model):
    title = models.CharField(max_length=400)
    date_created = models.DateTimeField('date created', default=current_time_with_tz, blank=True)


class SuggestedTime(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()


class Participant(models.Model):
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    name = models.CharField(max_length=200)
    suggested_times = models.ManyToManyField(SuggestedTime)

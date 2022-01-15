from django.test import TestCase
from django.urls import reverse
from django.core.exceptions import ObjectDoesNotExist
from django.utils.timezone import make_aware
from .models import Event, Participant, SuggestedTime
from datetime import datetime


def create_event(title):
    return Event.objects.create(title=title)


def create_participant(participant_name, event):
    return Participant.objects.create(name=participant_name, event=event)


def create_suggested_time(participant, start_time, end_time):
    start_time = make_aware(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'))
    end_time = make_aware(datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'))
    return SuggestedTime.objects.create(event=participant.event, start_time=start_time, end_time=end_time)


class eventTests(TestCase):
    def test_event_submit(self):
        title = "this is a test event"
        url = reverse('scheduling:submit_event')
        response = self.client.post(url, data={"title": title}, follow=True)
        self.assertContains(response, title)
        index_url = reverse('scheduling:index')
        self.assertRedirects(response, status_code=302, target_status_code=200, msg_prefix='',
                             fetch_redirect_response=True, expected_url=index_url)

    def test_event_delete(self):
        title = "this is a test event"
        event = create_event(title=title)
        # index_url = reverse('scheduling:index')
        # response = self.client.get(index_url)
        # self.assertContains(response, title)
        url = reverse('scheduling:delete_event')
        response = self.client.post(url, data={'event-id': event.id}, follow=True)
        self.assertNotContains(response, title)

    def test_participant_add(self):
        title = "this is a test event"
        event = create_event(title=title)
        # event_url = reverse('scheduling:event', args=(event.id,))
        # response = self.client.get(event_url)
        url = reverse('scheduling:add_participant', args=(event.id,))
        participant_name = 'test participant'
        response = self.client.post(url, data={'participant-name': participant_name}, follow=True)
        self.assertContains(response, participant_name)

    def test_participant_delete(self):
        title = "this is a test event"
        event = create_event(title=title)
        participant_name = 'test participant'
        participant = create_participant(participant_name=participant_name, event=event)
        url = reverse('scheduling:delete_participant')
        response = self.client.post(url, data={'participant-id': participant.id}, follow=True)
        self.assertNotContains(response, participant_name)

    def test_add_suggested_time(self):
        title = "this is a test event"
        event = create_event(title=title)
        participant_name = 'test participant'
        participant = create_participant(participant_name=participant_name, event=event)
        url = reverse('scheduling:add_suggested_time', args=(participant.id,))
        start_time = "2020-05-05 03:05:00"
        end_time = "2020-05-06 04:05:10"
        self.client.post(url, data={'start-time': start_time, 'end-time': end_time})
        url = reverse('scheduling:participant', args=(participant.id,))
        response = self.client.get(url)
        self.assertContains(response, start_time[:10])
        self.assertContains(response, end_time[:10])

    def test_delete_suggested_time(self):
        title = "this is a test event"
        event = create_event(title=title)
        participant_name = 'test participant'
        participant = create_participant(participant_name=participant_name, event=event)
        start_time = "2020-05-05 03:05:00"
        end_time = "2020-05-06 04:05:10"
        suggested_time = create_suggested_time(participant=participant, start_time=start_time, end_time=end_time)
        url = reverse('scheduling:delete_suggested_time')
        self.client.post(url, data={'suggested-time-id': suggested_time.id})
        url = reverse('scheduling:participant', args=(participant.id,))
        response = self.client.get(url)
        self.assertNotContains(response, start_time[:10])
        self.assertNotContains(response, end_time[:10])

    def test_event_participant_cascade(self):
        title = "this is a test event"
        event = create_event(title=title)
        participant_name = 'test participant'
        participant = create_participant(participant_name=participant_name, event=event)
        event.delete()
        with self.assertRaises(ObjectDoesNotExist):
            Participant.objects.get(pk=participant.id)

    def test_event_suggested_time_cascade(self):
        title = "this is a test event"
        event = create_event(title=title)
        participant_name = 'test participant'
        participant = create_participant(participant_name=participant_name, event=event)
        start_time = "2020-05-05 03:05:00"
        end_time = "2020-05-06 04:05:10"
        suggested_time = create_suggested_time(participant=participant, start_time=start_time, end_time=end_time)
        event.delete()
        with self.assertRaises(ObjectDoesNotExist):
            SuggestedTime.objects.get(pk=suggested_time.id)

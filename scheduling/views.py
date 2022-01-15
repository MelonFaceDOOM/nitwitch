from .models import Event, Participant, SuggestedTime
from django.views import generic
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.utils.timezone import make_aware
from datetime import datetime


class IndexView(generic.ListView):
    template_name = "scheduling/index.html"
    context_object_name = "latest_events_list"

    def get_queryset(self):
        """Return last 5 published articles"""
        return Event.objects.order_by('-date_created')[:5]


class EventView(generic.DetailView):
    model = Event
    template_name = 'scheduling/event.html'


def create_event(request):
    # Render the HTML template index.html
    return render(request, 'scheduling/create_event.html')


def submit_event(request):
    try:
        title = request.POST['title']
    except KeyError:
        return HttpResponseRedirect(reverse('scheduling:create_event'))
    else:
        event = Event(title=title)
        event.save()
        return HttpResponseRedirect(reverse('scheduling:index'))


def delete_event(request):
    try:
        event_id = request.POST['event-id']
    except KeyError:
        return HttpResponseRedirect(reverse('scheduling:index'))
    else:
        event = get_object_or_404(Event, pk=event_id)
        event.delete()
        return HttpResponseRedirect(reverse('scheduling:index'))


class ParticipantView(generic.DetailView):
    model = Participant
    template_name = 'scheduling/participant.html'


def delete_participant(request):
    try:
        participant_id = request.POST['participant-id']
    except KeyError:
        return HttpResponseRedirect(reverse('scheduling:index'))
    else:
        participant = get_object_or_404(Participant, pk=participant_id)
        event_id = participant.event.id
        participant.delete()
        return HttpResponseRedirect(reverse('scheduling:event', args=(event_id,)))


def add_participant(request, event_id):
    event = get_object_or_404(Event, pk=event_id)
    try:
        participant_name = request.POST['participant-name']
    except KeyError:
        return HttpResponseRedirect(reverse('scheduling:event', args=(event_id,)))
    else:
        participant = Participant(name=participant_name, event=event)
        participant.save()
        return HttpResponseRedirect(reverse('scheduling:event', args=(event_id,)))


def add_suggested_time(request, participant_id):
    try:
        start_time = request.POST['start-time']
        end_time = request.POST['end-time']
    except KeyError:
        return HttpResponseRedirect(reverse('scheduling:index'))
    else:
        start_time = make_aware(datetime.strptime(start_time, '%Y-%m-%d %H:%M:%S'))
        end_time = make_aware(datetime.strptime(end_time, '%Y-%m-%d %H:%M:%S'))
        participant = get_object_or_404(Participant, pk=participant_id)
        event = get_object_or_404(Event, pk=participant.event_id)
        suggested_time = SuggestedTime(event=event, start_time=start_time, end_time=end_time)
        suggested_time.save()
        participant.suggested_times.add(suggested_time)
        return HttpResponseRedirect(reverse('scheduling:event', args=(participant.event_id,)))


def delete_suggested_time(request):
    try:
        suggested_time_id = request.POST['suggested-time-id']
    except KeyError:
        return HttpResponseRedirect(reverse('scheduling:index'))
    else:
        suggested_time = get_object_or_404(SuggestedTime, pk=suggested_time_id)
        event_id = suggested_time.event.id
        suggested_time.delete()
        return HttpResponseRedirect(reverse('scheduling:event', args=(event_id,)))

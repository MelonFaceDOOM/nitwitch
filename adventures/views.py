import json
from .models import Adventure, GameCard, CardOption
from django.views import generic
from django.http import HttpResponseRedirect, JsonResponse, HttpResponse
from django.urls import reverse
from django.shortcuts import get_object_or_404, render
from django.views.decorators.http import require_POST
from accounts.permissions import admin_required
from django.core.paginator import Paginator
from django.db import transaction
from .parsers.validate_game_cards import adventure_is_valid


class IndexView(generic.ListView):
    context_object_name = "latest_adventures_list"
    template_name = "adventures/index.html"
    paginate_by = 5

    def get_queryset(self):
        return Adventure.objects.order_by('-pub_date')

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context['background_grid_class'] = 'background-grid background-grid-medium'
        return context


def adventure_game_card(request, title, card_id):
    adventure = get_object_or_404(Adventure, title=title)
    game_card = get_object_or_404(GameCard, adventure=adventure, card_id=card_id)
    adventure.view_count += 1
    adventure.save()
    return render(request, 'adventures/adventure_game_card.html', {'game_card': game_card})


def game_tree(request, title):
    adventure = get_object_or_404(Adventure, title=title)
    return render(request, 'adventures/game_tree.html', {'adventure': adventure})


def game_content(request, title):
    adventure = get_object_or_404(Adventure, title=title)
    adventure_dict = {"title": adventure.title, "author": adventure.author, "category": adventure.category, 'cards': []}
    for game_card in adventure.game_cards.all():
        game_card_dict = {"card_id": game_card.card_id,
                          "card_text": game_card.card_text,
                          "options": []}
        for option in game_card.card_options.all():
            option_dict = {"option_text": option.option_text,
                           "linked_card_id": option.linked_card_id}
            game_card_dict['options'].append(option_dict)
        adventure_dict['cards'].append(game_card_dict)
    return JsonResponse(adventure_dict)


@admin_required
@transaction.atomic
def submit_adventures(request):
    if request.method == "POST":
        # CardOption.objects.all().delete()
        # GameCard.objects.all().delete()
        # Adventure.objects.all().delete()
        adventure_files = request.FILES.getlist("adventure_files")
        try:
            for adventure_file in adventure_files:
                try:
                    adventure_json = json.load(adventure_file)
                except json.JSONDecodeError:
                    return HttpResponse(f"Invalid JSON file {adventure_file}", status=400)
                if not adventure_is_valid(adventure_json):
                    return HttpResponse(
                        f"issues found with game card file format (see parsers/validate_game_cards.py) for file {adventure_file}",
                        status=500)
                adventure = Adventure(title=adventure_json['title'],
                                      author=adventure_json['author'],
                                      category=adventure_json['category'],
                                      description=adventure_json.get('description', ''))
                adventure.save()
                for card_json in adventure_json['cards']:
                    game_card = GameCard(adventure=adventure,
                                         card_id=card_json['card_id'],
                                         card_text=card_json['card_text'])
                    game_card.save()
                    for option_json in card_json['options']:
                        card_option = CardOption(parent_card=game_card,
                                                 linked_card_id=option_json['linked_card_id'],
                                                 option_text=option_json['option_text'])
                        card_option.save()
        except Exception as e:
            return HttpResponse(f"Error processing file: {e}", status=500)
        return HttpResponseRedirect(reverse('adventures:index'))
    else:
        return HttpResponse("Invalid request method", status=405)


@admin_required
@require_POST
def delete_adventure(request, adventure_id):
    article = get_object_or_404(Adventure, pk=adventure_id)
    article.delete()
    return HttpResponseRedirect(reverse('adventures:index'))

def get_adventure_titles(request):
    adventure_titles = Adventure.objects.values_list('title', flat=True)
    return JsonResponse(list(adventure_titles), safe=False)
import os
import re
import json
from adventures.parsers.game_objects import GameCard


ADVENTURES_FOLDER = 'adventures'
ADVENTURE_NAME = "whoopdeedoo"


def adventure_is_valid(adventure_json):
    game_cards = []
    for game_card_dict in adventure_json['cards']:
        game_card = GameCard.create_from_dict(game_card_dict)
        game_cards.append(game_card)
    game_cards = sorted(game_cards, key=card_sort)
    first_card = game_cards[0]
    game_cards_found = [first_card]
    for found_card in walk_branches(game_cards, first_card):
        game_cards_found.append(found_card)
    if len(game_cards) == len(game_cards_found):
        return True
    else:
        return False


def is_game_card(filepath):
    filename = os.path.basename(filepath)
    pattern = rf"{ADVENTURE_NAME}_\d+_card.json"
    match = re.match(pattern, filename)
    if match:
        return True
    else:
        return False


def walk_branches(game_cards, game_card):
    for option in game_card.options:
        linked_card = get_card_by_id(game_cards, option.linked_card_id)
        yield linked_card
        if linked_card is None:
            raise ValueError(f"card {game_card.card_id} links to missing card with id {option.linked_card_id}")
        for found_card in walk_branches(game_cards, linked_card):
            yield found_card


def card_sort(card):
    # condition 1: lower length is smaller
    # condition 2: left-to-right sorting of card_id values
    return (len(card.card_id), card.card_id)


def get_card_by_id(cards, card_id):
    for card in cards:
        if card.card_id == card_id:
            return card


def get_card_id(filename):
    pattern = r".*?(\d*)_card.json"
    match = re.match(pattern, filename)
    return match.group(1)


def get_filepaths_from_folder(folder_path):
    filepaths = []
    for subdir, dirs, files in os.walk(folder_path):
        for file in files:
            filepath = os.path.join(subdir, file)
            filepaths.append(filepath)
    return filepaths


if __name__ == "__main__":
    main()

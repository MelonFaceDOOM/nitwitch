from dataclasses import dataclass
import json


@dataclass()
class CardOption:
    parent_card_id: str
    linked_card_id: str
    option_text: str = ""

    def __repr__(self):
        return f"CardOption <{self.parent_card_id}, linking to {self.linked_card_id}>: {self.option_text[:50]}{'...' if len(self.option_text) > 50 else ''} "


"""
card id system

000  001 010
  \  /   /
   00  01
    \ /
     0
child is parent + another digit. 
"""


class GameCard:
    def __init__(self, card_text="", option_texts=None, card_id=None):
        self.card_text = card_text
        self.card_id = card_id
        self.options = []
        if option_texts:
            self.add_options(option_texts)

    @classmethod
    def make_first_game_card(cls):
        card = GameCard(card_id="0")
        return card

    @classmethod
    def create_from_dict(cls, card_dict):
        card = GameCard(card_id=card_dict['card_id'])
        card.card_text = card_dict['card_text']
        for option_text in card_dict['options']:
            card.add_option(option_text)
        return card

    def _find_highest_child_option_number(self):
        if not self.options:
            return None
        highest_option_number = 0
        for option in self.options:
            option_number = int(option.linked_card_id[-1])  # last digit of card_id is option number
            if option_number >= highest_option_number:
                highest_option_number = option_number
        return highest_option_number

    def add_option(self, option_text):
        if not self.options:
            option_number = 0
        else:
            highest_child_option_number = self._find_highest_child_option_number()
            option_number = highest_child_option_number + 1
        card_id = self.card_id + str(option_number)
        option = CardOption(parent_card_id=self.card_id,
                            linked_card_id=card_id,
                            option_text=option_text)
        self.options.append(option)

    def add_options(self, option_texts):
        for option_text in option_texts:
            self.add_option(option_text)

    def to_dict(self):
        new_dict = {
            'card_text': self.card_text,
            'card_id': self.card_id,
            'options': []
        }
        for option in self.options:
            option_dict = {
                'parent_card_id': option.parent_card_id,
                'linked_card_id': option.linked_card_id,
                'option_text': option.option_text
            }
            new_dict['options'].append(option_dict)
        return new_dict

    def __repr__(self):
        return f"GameCard <{self.card_id}>: {self.card_text[:50]}{'...' if len(self.card_text) > 50 else ''} "


def save_objs(objs, save_location):
    with open(save_location, "w") as json_file:
        json.dump([obj.__dict__ for obj in objs], json_file, indent=4)


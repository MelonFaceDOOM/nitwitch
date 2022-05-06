import json
import os
from markup.tags import tags
import re


class FormatTag():
    def __init__(self, name, start, end, output_template, format_func):
        self.name = name
        self.start = start
        self.end = end
        self.format_func = format_func
        self.output_template = output_template
        self.openings = []

    def close(self, unformatted, end_pos):
        if self.openings:
            pre_text = unformatted[:self.openings[-1]]
            post_text = unformatted[end_pos + len(self.end):]
            tagged_text = unformatted[self.openings[-1]: end_pos + len(self.end)]
            formatted = self.format_func(self, tagged_text)
            self.openings = self.openings[:-1]
            return pre_text + formatted + post_text
        else:
            return unformatted


def create_tags():
    format_tags = []
    for t in tags:
        format_tags.append(FormatTag(name=t['name'], start=t['start'], end=t['end'],
                                     output_template=t['output_template'], format_func=t['format_func']))
    return format_tags


def parse(s):
    # the FormatTag class keeps track of information for each tag type, while variables within this function
    # are responsible for keeping track of inter-tag information and adjusting the tag values based on what happens
    # as the string is parsed
    replace = [
        (u'&', u'&amp;'),
        (u'<', u'&lt;'),
        (u'>', u'&gt;'),
        (u'\n', u'<br/>')
    ]
    
    for r in replace:
        s = s.replace(r[0], r[1])

    tags = create_tags()
    open_bracket_pos = None
    pos = 0
    while True:
        if pos >= len(s):
            return s
        # encountering end tags
        elif s[pos:pos + 2] == "[/":
            tag_identified = False
            for tag in tags:
                if s[pos:].startswith(tag.end):
                    tag_identified = True
                    if tag.openings:
                        tag_opening_pos = tag.openings[-1]
                        len_before = len(s)
                        s = tag.close(s, pos)

                        # find if any tags were between the start and close of the tag that was just closed
                        inbetween_tags = False
                        for _tag in tags:
                            for i, _tag_opening_pos in enumerate(_tag.openings):
                                if _tag_opening_pos > tag_opening_pos and _tag_opening_pos < pos:
                                    inbetween_tags = True
                                    del _tag.openings[
                                        i]  # delete in-between tags as their position value is no longer valid

                        if inbetween_tags:
                            # restart the parser at that the start location of the tag that was closed
                            pos = tag_opening_pos
                            break

                        # if there were no tags between, adjust the frame to the ending of this tag pairing)
                        pos += len(tag.end) + len(s) - len_before
                        break
                    else:
                        # if there is an end tag with no opening tag, skip past it.
                        pos += len(tag.end)
                        break

            if not tag_identified:
                pos += 2

        # encountering the start of opening tags
        elif s[pos] == "[":
            open_bracket_pos = pos
            pos += 1
        # encountering the end of opening tags
        elif s[pos] == "]":
            if open_bracket_pos is not None:
                possible_start_tag = s[open_bracket_pos:pos + 1]
                for tag in tags:
                    if bool(re.match(tag.start, possible_start_tag)):
                        tag.openings.append(open_bracket_pos)
                        open_bracket_pos = None
                        break
            pos += 1
        else:
            pos += 1
        # print(pos, s[:pos])

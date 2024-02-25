import argparse
from os import environ
from pathlib import Path
import re
from turtle import update
import genanki

def replace_dollar_signs_and_commands(to_replace: str, commands: dict[str, str]) -> str:
    updated = to_replace
    matches = re.findall(r"\$\$.*?\$\$|\$.*?\$", updated) # filtering out every math element
    # first replace the opening $ and $$ with the corresponding anki mathjax elements
    updated_matches = list(map(lambda x: x.replace("$", "&nbsp;<anki-mathjax>", 1), matches))
    updated_matches = list(map(lambda x: x.replace("$$", "&nbsp;<anki-mathjax>", 1), updated_matches))
    # second replace the closing $ and $4 with the closing anki mathjax tag
    updated_matches = list(map(lambda x: x.replace("$", "</anki-mathjax>"), updated_matches))
    updated_matches = list(map(lambda x: x.replace("$$", "</anki-mathjax>"), updated_matches))

    for i in range(len(updated_matches)): # replace self-defined latex commands by their original version
        for key in list(predefined_commands.keys()):
            updated_matches[i] = updated_matches[i].replace(key, predefined_commands[key])

    for i in range(len(matches)):
        updated = updated.replace(matches[i], updated_matches[i])

    return updated

def replace_list(to_replace: str, is_ordered: bool) -> str:
    if is_ordered:
        replaced = to_replace.replace("\\begin{enumerate}", "<ol>")
        replaced = replaced.replace("\\end{enumerate}", "</ol>")
    else:
        replaced = to_replace.replace("\\begin{itemize}", "<ul>")
        replaced = replaced.replace("\\end{itemize}", "</ul>")

    replaced = replaced.replace("\\item", "<li>")
    items = replaced.split("<li>")
    del items[0] # only the list items are relevant
    del items[-1]

    for i in range(len(items)):
        replaced = replaced.replace(items[i],  items[i] + "</li>")

    return replaced
    


# genanki model
model = genanki.Model(
  1607392319,
  'Simple Model',
  fields=[
    {'name': 'Question'},
    {'name': 'Answer'},
  ],
  templates=[
    {
      'name': 'Card 1',
      'qfmt': '{{Question}}',
      'afmt': '{{FrontSide}}<hr id="answer">{{Answer}}',
    },
  ])


# parse the arguments
parser = argparse.ArgumentParser(description="Create flashcards for the specified script.")
parser.add_argument("filename", help="the latex file from which the cards will be generated")
parser.add_argument('-s', '--section', required=False, help="specifies the section from which the flashcards will be created, default: last section", type=int)
args = parser.parse_args()

filename = args.filename
section_number = args.section

# read the contents of the specified file
path = Path(args.filename)
contents = path.read_text(encoding="utf-8")

predefined_commands = {}
commands = contents.split("\\newcommand{")
del commands[0]
del commands[-1]
for command in commands:
    separated = command.split("}{")
    separated[1] = separated[1][:-2] # removes the newline character and the closing curly brace
    predefined_commands[separated[0]] = separated[1]

# split for sections
sections = contents.split("\section")
del sections[0] # remove the preamble in which only commands etc are defined

# find out the relevant section
relevant_section = None
if section_number == None:
    relevant_section = sections[-1]
elif section_number > len(sections):
    raise ValueError("The given section number is greater than the number of available sections.")
elif section_number <= 0:
    raise ValueError("The section number has to be greater or equal to 1.")
else:
    relevant_section = sections[section_number-1]

# remove the escape characters
escapes = ''.join([chr(char) for char in range(1, 32)])
translator = str.maketrans('', '', escapes)
relevant_section = relevant_section.translate(translator)
environments = re.split("begin{definition}|begin{satz}|begin{bemerkung}", relevant_section)

# get the name of the section as a title for the anki deck
section_name = environments[0]
section_name = section_name.removeprefix("{")
if "subsection" in section_name:
    section_name = section_name[:section_name.rfind("subsection")-1]
section_name = section_name.removesuffix("}\\")
section_name = section_name.removesuffix("}")

del environments[0]

cards = []

for environment in environments:
    if not "satz" in environment:
        question_answer_separated = environment.split("}",1)
        question = question_answer_separated[0]
        question = question.lstrip("{")
        answer = question_answer_separated[1]
        
    else:
        question_answer_separated = environment.split("}",2)
        question = f"Satz {question_answer_separated[0].lstrip('{')}: {question_answer_separated[1].lstrip('{')}"
        answer = question_answer_separated[2]

    answer = answer.lstrip("{")
    if "end{definition}" in answer:
        answer = answer[:answer.rfind("end{definition}")-1]
    elif "end{bemerkung}" in answer:
        answer = answer[:answer.rfind("end{bemerkung}")-1]
    else:
        answer = answer[:answer.rfind("end{satz}")-1]
    
    question = replace_dollar_signs_and_commands(question, predefined_commands)
    answer = replace_dollar_signs_and_commands(answer, predefined_commands)

    if "itemize" in answer:
        answer = replace_list(answer, False)
    
    if "enumerate" in answer:
        answer = replace_list(answer, True)

    cards.append(genanki.Note(
        model=model,
        fields=[question, answer]
    ))

# create anki deck
deck = genanki.Deck(
    2059400110,
    f"{section_name}"
)

for card in cards:
    deck.add_note(card)

genanki.Package(deck).write_to_file(f"{section_name}.apkg")
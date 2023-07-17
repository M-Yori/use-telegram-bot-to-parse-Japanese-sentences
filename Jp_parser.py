
"""This telegram bot is used to parse Japanese sentences in a clear way"""
# requirement:
# pip install spacy==2.3.5 ja-ginza==4.0.0 ginza==4.0.5
# PTB 20.1, python 3.9


import telegram
import logging
from telegram import Update
from telegram.constants import ParseMode
from telegram.ext import Application, ApplicationBuilder, Updater, ContextTypes, CommandHandler, MessageHandler, filters, CallbackContext
import spacy
from spacy import displacy
import sys
import ginza


logging.basicConfig(
    # filename='logAtome.txt',
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)
# Set up Telegram bot
token = 'YOUR_BOT_TOKEN_HERE'

bot = telegram.Bot(token)



class DependencyAnalysis:
    def __init__(self):
        self.nlp = spacy.load('ja_ginza')
        self.sents = []

    def run(self, text):
        doc = self.nlp(text)
        for sent in doc.sents:
            self.sents.append(sent)
        return self.sents

def to_dependency_data(sentence):
    # per sentence
    arcs = []
    words = []
    head_list = ginza.bunsetu_head_list(sentence)
    spans = ginza.bunsetu_spans(sentence)

    list_parents = []

    for i, chunk in enumerate(spans):
        words.append(chunk)
        for token in chunk.lefts:
            list_parents.append(head_list.index(token.i))
            arcs.append({
                'start': head_list.index(token.i),
                'end': i,
                'dep': token.dep_,
            })
        for token in chunk.rights:
            pass # TODO

    indices = list(range(len(words)))

    root_idx = set(list_parents).symmetric_difference(indices).pop()
    root_part = words[root_idx]
    arcs.append({
        'start': root_idx,
        'end': "root",
        'dep': "root",
    })

    idx = root_idx
    item = words[root_idx]

    return arcs, spans, words, (root_idx, root_part)




async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    await context.bot.send_message(chat_id=chat_id, text="Hi! Send me a Japanese sentence and I will parse it for you.", reply_to_message_id=message_id, parse_mode=ParseMode.HTML)



def print_tree(words, arcs, idx, level=0):
    indent = "\. " * 2 * level
    word = words[idx]
    dep = arcs[idx]['dep']
    # Get the corresponding token within the span
    token = word.root.head
    # Format the text based on the level
    if level < 2:
        # Format text as bold for first two levels
        # formatted_text = f"*{word.text}* ({word.label_}/{dep})"
        formatted_text = f"*{indent}{word.text}*" #I deleted the ({word.label_}/{dep}) part here in this line because they are not needed for me.
    # elif token.pos_ == 'ADJ':
    #     # Format adjectives with strikethrough
    #     formatted_text = f"~{indent}{word.text}~"
    else:
        # formatted_text = f"{indent}{word.text} ({word.label_}/{dep})"
        formatted_text = f"{indent}{word.text}" #I deleted the ({word.label_}/{dep}) part here in this line because they are not needed for me.

    children_idx = [x['start'] for x in arcs if x['end'] == idx]

    # If there are no child nodes
    if not children_idx:
        # Check if the parent has other children at the same level
        parent_idx = arcs[idx]['start']
        sibling_idxs = [x['end'] for x in arcs if x['start'] == parent_idx and x['end'] != idx]

        # Format text as spoiler for leaf nodes if there are no siblings at the same level
        if level >= 2 and sibling_idxs:
            return [f"||_{indent}\({word.text}\)_||"]
        else:
            return [formatted_text]

    # Sort child nodes in descending order
    children_idx.sort(reverse=True)

    children = [words[i] for i in children_idx]

    out = []
    for i, x in zip(children_idx, children):
        item = print_tree(words, arcs, i, level+1)
        out.extend(item)
    return [formatted_text] + out



async def parse(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    chat_id = update.message.chat_id
    message_id = update.message.message_id
    sentence = update.message.text

    dependency = DependencyAnalysis()
    dependency.run(sentence)
    doc_head = dependency.sents[0]
    arcs, spans, words, root = to_dependency_data(doc_head)

    # Creating a string instead of printing
    tree = print_tree(words, arcs, root[0])
    tree_string = '\n'.join(tree)

    await context.bot.send_message(chat_id=chat_id, text=tree_string, reply_to_message_id=message_id, parse_mode=ParseMode.MARKDOWN_V2)




def main() -> None:
    """Run the bot."""
    # Create the Application and pass it your bot's token.
    app = (
        Application.builder()
        .token(token)
        .build()
    )
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, parse))
    app.run_polling()




if __name__ == "__main__":
    main()

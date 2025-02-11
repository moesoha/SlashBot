import os
import re
from typing import List, Dict, Union

import requests
from telegram.ext import Updater, MessageHandler, filters

TELEGRAM = 777000
GROUP = 1087968824
Filters = filters.Filters
parser = re.compile(r'^\/((?:[^ 　\\]|\\.)+)([ 　]*)(.*)$')
escaping = ('\\ ', '\\　')

# Docker env
if os.environ.get('TOKEN') and os.environ['TOKEN'] != 'X':
    Token = os.environ['TOKEN']
else:
    raise Exception('no token')


# Find someone's full name by their username
def find_name_by_username(username: str) -> str:
    r = requests.get(f'https://t.me/{username.replace("@", "")}')
    return re.search('(?<=<meta property="og:title" content=").*(?=")', r.text, re.IGNORECASE).group(0)


def get_user(msg):
    if msg['from']['id'] == TELEGRAM:
        return {'first_name': msg['forward_from_chat']['title'], 'id': msg['forward_from_chat']['id']}
    elif msg['from']['id'] == GROUP:
        return {'first_name': msg['chat']['title'], 'id': msg['chat']['id']}
    else:
        return msg['from']


def get_users(msg):
    msg_from = msg
    if 'reply_to_message' in msg.keys():
        msg_rpl = msg['reply_to_message']
    else:
        msg_rpl = msg_from.copy()
    from_user, rpl_user = get_user(msg_from), get_user(msg_rpl)

    # Not replying to anything
    if rpl_user == from_user:

        # Detect if the message contains a mention. If it has, use the mentioned user.
        entities: List[Dict[str, Union[str, int]]] = msg['entities']
        mentions = [e for e in entities if e['type'] == 'mention']
        if mentions:

            # Find username
            offset = mentions[0]['offset']
            length = mentions[0]['length']
            text = msg['text']
            username = text[offset : offset + length]
            rpl_user = {'first_name': find_name_by_username(username), 'username': username}

            # Remove mention from message text
            msg['text'] = text[:offset] + text[offset + length:]

        else:
            rpl_user = {'first_name': '自己', 'id': rpl_user['id']}

    return from_user, rpl_user


# Create mention string from user
def mention(user: Dict[str, str]) -> str:

    # Combine name
    last = user.get('last_name', '')
    first = user['first_name']
    name = first + (f' {last}' if last else '')

    # Create user reference link
    username = user.get('username', '')
    uid = user.get('id', '')
    link = f'tg://resolve?domain={username}' if username else f'tg://user?id={uid}'

    return f"[{name}]({link})"


def get_text(mention_from, mention_rpl, command):
    parsed = list(parser.search(delUsername.sub('', command)).groups())
    for escape in escaping:
        parsed[0] = parsed[0].replace(escape, escape[1:])
    if parsed[0] == 'me':
        return f"{mention_from}{bool(parsed[1])*' '}{parsed[2]}！"
    elif parsed[0] == 'you':
        return f"{mention_rpl}{bool(parsed[1])*' '}{parsed[2]}！"
    elif parsed[2]:
        return f"{mention_from} {parsed[0]} {mention_rpl} {parsed[2]}！"
    else:
        return f"{mention_from} {parsed[0]} 了 {mention_rpl}！"


def reply(update, context):
    print(update.to_dict())
    msg = update.to_dict()['message']
    from_user, rpl_user = get_users(msg)

    # Escape markdown
    command = msg['text']
    command = command.replace("_", "\\_").replace("*", "\\*").replace("[", "\\[").replace("`", "\\`")

    text = get_text(mention(from_user), mention(rpl_user), command)
    print(text, end='\n\n')

    update.effective_message.reply_text(text, parse_mode='Markdown')


if __name__ == '__main__':
    updater = Updater(token=Token, use_context=True)
    delUsername = re.compile('@' + updater.bot.username, re.I)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.regex(parser), reply))

    updater.start_polling()
    updater.idle()

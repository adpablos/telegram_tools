import csv
import datetime
import json
import random
import re
import time
import traceback

from easychatgpt import ChatClient
from telethon import functions
from telethon.errors.rpcerrorlist import PeerFloodError, UserPrivacyRestrictedError, FloodWaitError
from telethon.sync import TelegramClient
from telethon.tl.functions.channels import InviteToChannelRequest, CreateChannelRequest
from telethon.tl.functions.messages import GetDialogsRequest
from telethon.tl.types import InputPeerEmpty, InputPeerChannel, InputPeerUser, Channel, Chat, InputUser

WAIT_BETWEEN_OPERATION = 120

WAIT_BETWEEN_CHUNKS = 900

USERS_CHUNK = 35

ERRORS_ALLOWED = 3

config = {}


def evaluate_sleep_message(message):
    seconds_str = re.findall('\d+', message)
    if seconds_str:
        countdown(int(str(seconds_str[0])) + random.randint(60, 180))


def scrap_members(client):
    print("Scrapping members.")
    group = get_group_by_user_input(client, True)
    print('Fetching Members...')
    all_participants = client.get_participants(group, aggressive=True)
    print('Saving In file...')
    with open("data/members.csv", "w", encoding='UTF-8') as f:
        writer = csv.writer(f, delimiter=",", lineterminator="\n")
        writer.writerow(['username', 'user id', 'access hash', 'name', 'group', 'group id', 'group hash'])
        for user in all_participants:
            if user.username:
                username = user.username
            else:
                username = ""
            if user.first_name:
                first_name = user.first_name
            else:
                first_name = ""
            if user.last_name:
                last_name = user.last_name
            else:
                last_name = ""
            name = (first_name + ' ' + last_name).strip()
            writer.writerow([username, user.id, user.access_hash, name, group.title, group.id, group.hash])
    print('Members scraped successfully.')


def get_users_from_file(file_path):
    users = []
    with open(file_path, encoding='UTF-8') as f:
        rows = csv.reader(f, delimiter=",", lineterminator="\n")
        next(rows, None)
        for row in rows:
            user = {'username': row[0], 'id': int(row[1]), 'access_hash': int(row[2]), 'name': row[3]}
            users.append(user)
    return users


def get_users_from_participants(participants):
    users = []
    for participant in participants:
        users.append(
            {'username': participant.username, 'id': int(participant.id), 'access_hash': int(participant.access_hash),
             'name': participant.first_name + ' ' + participant.last_name})
    return users


def evaluate_errors(num_errors):
    if num_errors >= ERRORS_ALLOWED:
        print(str(ERRORS_ALLOWED) + " number of errors reached.")
        quit()


def add_members_progressively(client, group_entity, users):
    num_errors = 0
    iteration = 0
    members_added = 0
    for user in users:
        iteration += 1
        if iteration % USERS_CHUNK == 0:
            print("Waiting " + str(WAIT_BETWEEN_CHUNKS) + " Seconds...")
            countdown(WAIT_BETWEEN_CHUNKS)
        try:
            print("Adding {}".format(user))

            updates = client(InviteToChannelRequest(channel=group_entity,
                                                    users=[InputUser(user_id=user['id'],
                                                                     access_hash=user['access_hash'])]))
            if len(updates.updates) > 0:
                print("User {} added.".format(user['first_name'] + ' ' + user['last_name']))
                members_added += 1
            else:
                print("User was already in the group.")
            print("Waiting " + str(WAIT_BETWEEN_OPERATION) + " Seconds...")
            countdown(WAIT_BETWEEN_OPERATION)
        except (PeerFloodError, FloodWaitError) as e:
            num_errors += 1
            print("Getting Flood Error from telegram operating with api_id {}.".format(client.api_id))
            traceback.print_exc()
        except UserPrivacyRestrictedError as e:
            num_errors += 1
            print("The user's privacy settings do not allow you to do this. Skipping.")
            traceback.print_exc()
        except Exception as e:
            num_errors += 1
            evaluate_sleep_message(str(e))
            print("Unexpected Error.")
            traceback.print_exc()
        finally:
            evaluate_errors(num_errors)

    print("Total members added: " + str(members_added))


def add_members(client, file_path):
    print("Adding members from " + file_path + ".")

    users = get_users_from_file(file_path)
    group = get_group_by_user_input(client, True)
    target_group_entity = InputPeerChannel(group.id, group.access_hash)

    add_members_progressively(client, target_group_entity, users)


def set_supergroup(client):
    print("Setting supergroup.")
    target_group = get_group_by_user_input(client, False)
    client(functions.messages.MigrateChatRequest(chat_id=target_group.id))


def get_chats(client):
    all_chats = []
    chats = []
    result = client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=200,
        hash=0
    ))
    chats.extend(result.chats)
    for chat in chats:
        if chat.title == 'Testing channel':
            all_chats.append(chat)
    return all_chats


def is_active(chat):
    return (isinstance(chat, Channel) or isinstance(chat, Chat)) and (
            not hasattr(chat, "deactivated") or (hasattr(chat, "deactivated") and not chat.deactivated))


def get_groups(client, megagroup):
    chats = []
    groups = []
    result = client(GetDialogsRequest(
        offset_date=None,
        offset_id=0,
        offset_peer=InputPeerEmpty(),
        limit=200,
        hash=0
    ))
    chats.extend(result.chats)
    for chat in chats:
        try:
            is_chat_active = is_active(chat)
            if is_chat_active:
                if megagroup is None or (not megagroup and not hasattr(chat, "megagroup") or not chat.megagroup) or \
                        (megagroup and hasattr(chat, "megagroup") and chat.megagroup):
                    groups.append(chat)
        except Exception as inst:
            print(type(inst))  # the exception instance
            print(inst.args)  # arguments stored in .args
            print(inst)  # __str__ allows args to be printed directly,
            continue
    return groups


def get_group_by_user_input(client, megagroup):
    groups = get_groups(client, megagroup)
    print('Choose a group: ')
    i = 0
    for group in groups:
        print(str(i) + '- ' + group.title)
        i += 1
    g_index = input("Enter the number: ")
    return groups[int(g_index)]


def get_group_by_title(client, megagroup, title):
    groups = get_groups(client, megagroup)
    result = None
    for group in groups:
        if group.title == title:
            result = group
            break
    return result


def countdown(t):
    while t:
        timer = 'Sleeping for ' + str(datetime.timedelta(seconds=t))
        print(timer, end="\r")
        time.sleep(1)
        t -= 1
    print()


def generate_session(configuration):
    sessions = []
    accounts = configuration['accounts']
    for account in accounts:
        api_id = account['api_id']
        api_hash = account['api_hash']
        phone = account['phone']
        print(phone)

        telegram_client = TelegramClient(configuration['session_folder_path'] + "/" + phone, api_id, api_hash)
        telegram_client.start()
        if telegram_client.is_user_authorized():
            print('Login success')
            sessions.append({"phone": phone, "client": telegram_client})
        else:
            print('Login fail due to user not authorized. A code has been sent to ' + phone)
            try:
                telegram_client.send_code_request(phone)
                telegram_client.sign_in(phone, input("Enter the code: "))
            except Exception as e:
                print('Error trying to login with ' + phone)
                print(str(e))
                continue
    return sessions


def create_super_group(client, channel):
    title = channel.title + "_group"
    result = get_group_by_title(client, True, title)
    if result is None:
        result = client(CreateChannelRequest(channel.title + "_group", "about", megagroup=True)).chats[0]

    return result


def migrate_channel_to_supergroup(client):
    channel_title = input("What is the title of your channel? ")
    channel = get_group_by_title(client, False, channel_title)
    if channel is not None:
        group = create_super_group(client, channel)

        channel_participants = client.get_participants(channel, aggressive=True)
        users = get_users_from_participants(channel_participants)
        users = users + get_users_from_file('data/members.csv')

        group_entity = client.get_entity(InputPeerChannel(group.id, group.access_hash))
        print(str(len(users)) + ' users to add in total.')
        add_members_progressively(client, group_entity, users)
    else:
        print('No channel found with {} name'.format(channel_title))


def summarize(client):
    to_summarize = ''
    group = get_group_by_user_input(client, None)

    for message in client.iter_messages(group, reverse=True, limit=100):
        if message.text is not None:
            # print(message.sender_id, ':', message.text)
            to_summarize = to_summarize + message.text + "\n"

    print('Text to summarize: ', to_summarize)

    chat = ChatClient("adpabloslopez+openai@gmail.com", "dwp*wpt0xvt-rjn7YPH")
    answer = chat.interact('Summarize the following text: ' + to_summarize)
    print(answer)


def menu(client):
    ans = True
    while ans:
        print("""
    1.Set supergroup
    2.Scrap members
    3.Migrate channel to supergroup
    4.Add members
    5.Summarize        
    6.Exit/Quit
        """)
        ans = input("What would you like to do? ")
        if ans == "1":
            print("\n Set supergroup")
            set_supergroup(client)
            ans = None
        elif ans == "2":
            print("\n Scrap members")
            scrap_members(client)
            ans = None
        elif ans == "3":
            print("\n Migrate channel to supergroup")
            migrate_channel_to_supergroup(client)
            ans = None
        elif ans == "4":
            print("\n Add members")
            add_members(client, 'data/members.csv')
            ans = None
        elif ans == "5":
            print("\n Sumarize")
            summarize(client)
            ans = None
        elif ans == "6":
            print("\n Exit")
            ans = None
        else:
            print("\n Not Valid Choice Try again")


if __name__ == "__main__":
    start_time = datetime.datetime.now()

    with open('config/config.json', 'r', encoding='utf-8') as f:
        config = json.loads(f.read())
    clients = generate_session(config)
    menu(clients[1]['client'])

    print("Total time: " + str(datetime.datetime.now() - start_time))

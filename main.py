import os
import json

from imap_tools import MailBox

####
FILENAME = os.environ['FILENAME']
SLACK_TOKEN = os.environ['SLACK_TOKEN']
SLACK_CHANNEL = os.environ['SLACK_CHANNEL']
IMAP_FOLDER_NAME = os.environ['IMAP_FOLDER_NAME']
IMAP_HOST = os.environ['IMAP_HOST']
IMAP_PASS = os.environ['IMAP_PASS']
IMAP_USER = os.environ['IMAP_USER']
IMAP_LIMIT = 15
####

def message_to_slack(message: str, channel=SLACK_CHANNEL):

    from slack import WebClient
    from slack.errors import SlackApiError

    slack_client = WebClient(token=SLACK_TOKEN)

    response = slack_client.chat_postMessage(
    channel=channel,
    text=message
    )

    return response


def get_new_message_headers(
    host: str, user: str, password: str, folder: str, limit: int = 10
) -> list:

    # open json, create json if not found
    try:
        file = open(FILENAME)
    except FileNotFoundError:
        defaults = {"uid_validity": 0, "most_recent_uid": 0,}
        with open(FILENAME, 'w') as f:
            json.dump(defaults, f, indent = 4)
        file = open(FILENAME)

    json_data = json.load(file)
    old_uid = json_data["most_recent_uid"]

    # create empty list to collect new messages (if any)
    new_messages_list = []

    with MailBox(host).login(user, password) as mailbox:
        mailbox.folder.set(IMAP_FOLDER_NAME)

        # check uid validity of folder, reset most_recent_uid to 0 if invalid
        folder_status = mailbox.folder.status(folder)
        if folder_status["UIDVALIDITY"] != json_data["uid_validity"]:
            print(f'uid_validity von {json_data["uid_validity"]} zu {folder_status["UIDVALIDITY"]} verändert!')
            json_data["uid_validity"] = folder_status["UIDVALIDITY"]
            json_data["most_recent_uid"] = 0

        # get message headers as iterator
        messages = mailbox.fetch(
            limit=limit,
            headers_only=True,
            reverse=True,
            mark_seen=False,
        )
        # convert iterator to list
        messages_list = list(messages)

        # save headers to dict
        for msg in messages_list:
            uid = int(msg.uid)
            most_recent_uid = int(json_data["most_recent_uid"])
            if most_recent_uid != 0 and uid > most_recent_uid:
                message_dict = {
                    "uid": uid,
                    "subject": msg.subject,
                    "from": msg.from_,
                    "date": msg.date,
                }
                new_messages_list.append(message_dict)
            elif most_recent_uid == 0:
                print("First run, no alert sent!")
            # else:
            #     print(f"Already known message with UID: {uid} Subject: \"{msg.subject}\"")

        # update JSON (if data has changed)
        json_data["most_recent_uid"] = int(messages_list[0].uid)
        print(f"json uid was:    {old_uid}")
        print(f'json uid is now: {json_data["most_recent_uid"]}')
        if json_data["most_recent_uid"] != old_uid:
            print("Saving new json data")
            with open('values.json', 'w') as f:
                json.dump(json_data, f, indent = 4)
        else:
            print("No new json data to save")

    return new_messages_list


def main():
    new_messages = get_new_message_headers(
        IMAP_HOST, IMAP_USER, IMAP_PASS, IMAP_FOLDER_NAME, IMAP_LIMIT
    )
    # print(messages)
    for msg in new_messages:
        slack_alert = f"✉ New mail: \"{msg['subject']}\" from {msg['from']}!"
        print(message_to_slack(slack_alert))


if __name__ == "__main__":
    main()

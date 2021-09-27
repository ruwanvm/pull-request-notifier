import datetime
import json

import requests
import yaml
import os
from os.path import join

import logging


def send_message(message_dict):
    if 'webhook.office.com' in message_dict['webhook_url']:
        message_dict['channel_type'] = "teams"

    if message_dict['channel_type'].lower() == "teams":
        payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "0076D7",
            "summary": message_dict['repo'],
            "sections": [{
                "activityTitle": message_dict['repo'],
                "activitySubtitle": message_dict['title'],
                "activityImage": message_dict['avatar'],
                "facts": [{
                    "name": "User",
                    "value": message_dict['user']['name']
                }, {
                    "name": "Created",
                    "value": message_dict['created']
                }, {
                    "name": "Head",
                    "value": f"{message_dict['head']['repo']}:{message_dict['head']['branch']}"
                }, {
                    "name": "Base ",
                    "value": f"{message_dict['base']['repo']}:{message_dict['base']['branch']}"
                }, {
                    "name": "Pull Request ",
                    "value": message_dict['url']
                }, {
                    "name": "Diff URL ",
                    "value": message_dict['diff_url']
                }],
                "markdown": True
            }]
        }
    elif message_dict['channel_type'].lower() == "slack":
        payload = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": message_dict['title']
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"""*User*: {message_dict['user']['name']}\n*Created*: {message_dict['created']}\n*Head* : {message_dict['head']['repo']}:{message_dict['head']['branch']}\n*Base* : {message_dict['base']['repo']}:{message_dict['base']['branch']}\n*Pull Request* : {message_dict['url']}\n*Diff URL* : {message_dict['diff_url']}"""
                    },
                    "accessory": {
                        "type": "image",
                        "image_url": message_dict['avatar'],
                        "alt_text": message_dict['repo']
                    }
                }
            ]
        }
    else:
        payload = {"text": f"""*User*: {message_dict['user']['name']}\n*Created*: {message_dict['created']}\n*Head* : {message_dict['head']['repo']}:{message_dict['head']['branch']}\n*Base* : {message_dict['base']['repo']}:{message_dict['base']['branch']}\n*Pull Request* : {message_dict['url']}\n*Diff URL* : {message_dict['diff_url']}"""}
    headers = {
        'Content-Type': 'application/json'
    }

    response = requests.post(message_dict['webhook_url'], data=json.dumps(payload), headers=headers)

    output = f"Notification is send with status {response.status_code}"

    return output


def main():
    config_file = 'app-config.yaml'

    cwd = os.getcwd()
    config_dir = join(cwd, 'conf')
    logs_dir = join(cwd, 'logs')

    log_file = join(logs_dir, 'pull-request-notifier.log')

    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s | pull-request-notifier |%("
                                                                      "levelname)s | %(message)s")
    logging.info('Started')

    status = 200
    notify_timedelta = 0

    # Read app configs
    if status == 200:
        try:
            with open(join(config_dir, config_file)) as config_file:
                app_configs = yaml.load(config_file, Loader=yaml.FullLoader)
            status = 200
            logging.info("Configurations are loaded")
            notify_timedelta = int(app_configs['notifications']['pull-open-days'])
        except Exception as e:
            status = 501
            logging.error(f"Error loading configurations\n{str(e)}")

    if status == 200:
        open_pulls = {}
        default_avatar = app_configs['default-avatar']
        default_channel = app_configs['default-channel']
        default_channel_type = app_configs['default-channel_type']
        github_token = os.environ[app_configs['github-bearer-token']]
        current_time = datetime.datetime.now()

        for repository in app_configs['repositories']:
            if "channel" in repository:
                channel = repository['channel']
            else:
                channel = default_channel
            if "avatar" in repository:
                avatar = repository['avatar']
            else:
                avatar = default_avatar
            if "channel_type" in repository:
                channel_type = repository['channel_type']
            else:
                channel_type = default_channel_type

            print(f"{repository['name']} repository is checking")

            open_pulls[repository['name']] = []
            url = f"https://api.github.com/repos/{repository['owner']}/{repository['name']}/pulls"

            payload = {}
            headers = {
                'Authorization': f'Bearer {github_token}'
            }
            response = requests.request("GET", url, headers=headers, data=payload)

            for open_pull in response.json():
                if open_pull['state'] == 'open':
                    updated_time = datetime.datetime.strptime(open_pull['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                    if current_time - datetime.timedelta(days=notify_timedelta) > updated_time:
                        pull_open_days = current_time - updated_time
                        print(f"...Pull request \"{open_pull['title']}\" is open for {pull_open_days.days} days")
                        open_pull_object = {
                            "channel_type": channel_type,
                            "repo": f"{repository['owner']}/{repository['name']}",
                            "webhook_url": os.environ[channel],
                            "avatar": avatar,
                            "title": f"Pull request - {open_pull['title']} is {open_pull['state']} for {pull_open_days.days} days",
                            "user": {
                                "name": open_pull['user']['login']
                            },
                            "details": open_pull['body'],
                            "created": open_pull['created_at'],
                            "assignees": open_pull['assignees'],
                            "url": open_pull['html_url'],
                            "diff_url": open_pull['diff_url'],
                            "head": {
                                "repo": open_pull['head']['repo']['full_name'],
                                "branch": open_pull['head']['ref'],
                                "url": f"{open_pull['head']['repo']['html_url']}/tree/{open_pull['head']['ref']}"
                            },
                            "base": {
                                "repo": open_pull['base']['repo']['full_name'],
                                "branch": open_pull['base']['ref'],
                                "url": f"{open_pull['base']['repo']['html_url']}/tree/{open_pull['base']['ref']}"
                            }
                        }

                        results = send_message(open_pull_object)

                        print(results)


if __name__ == "__main__":
    main()

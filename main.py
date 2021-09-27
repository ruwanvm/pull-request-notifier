import datetime
import json

import requests
import yaml
import os
from os.path import join

import logging


def send_message(message_dict):
    headers = {
        'Content-Type': 'application/json'
    }

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

    response = requests.post(message_dict['webhook_url'], data=json.dumps(payload), headers=headers)

    output = f"Notification is send with status {response.status_code}"

    return output


def main():
    config_file = 'dev-app-config.yaml'

    cwd = os.getcwd()
    config_dir = join(cwd, 'conf')
    logs_dir = join(cwd, 'logs')

    log_file = join(logs_dir, 'pull-request-notifier.log')

    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s | pull-request-notifier |%("
                                                                      "levelname)s | %(message)s")
    logging.info('Started')

    status = 200

    # Read app configs
    if status == 200:
        try:
            with open(join(config_dir, config_file)) as config_file:
                app_configs = yaml.load(config_file, Loader=yaml.FullLoader)
            status = 200
            logging.info("Configurations are loaded")
        except Exception as e:
            status = 501
            logging.error(f"Error loading configurations\n{str(e)}")

    if status == 200:
        open_pulls = []
        avatar = app_configs['default-avatar']
        channel = app_configs['default-channel']
        channel_type = app_configs['default-channel_type']
        current_time = datetime.datetime.now()
        for repository in app_configs['repositories']:
            if channel in repository:
                channel = repository['channel']
            if avatar in repository:
                avatar = repository['avatar']
            if channel_type in repository:
                channel_type = repository['channel_type']

            open_pulls_object = {
                'url': f"https://api.github.com/repos/{repository['owner']}/{repository['name']}/pulls",
                'channel': channel, 'type': channel_type, 'avatar': avatar}

            open_pulls.append(open_pulls_object)

        print(json.dumps(open_pulls, indent=4))



if __name__ == "__main__":
    main()

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
    secret_file = 'dev-secrets.json'
    config_file = 'dev-app-config.yaml'

    cwd = os.getcwd()
    secret_dir = join(cwd, 'secrets')
    config_dir = join(cwd, 'conf')
    logs_dir = join(cwd, 'logs')

    log_file = join(logs_dir, 'pull-request-notifier.log')

    logging.basicConfig(filename=log_file, level=logging.INFO, format="%(asctime)s | pull-request-notifier |%("
                                                                      "levelname)s | %(message)s")
    logging.info('Started')

    # Read secrets (GitHub auth token and teams webhook)
    try:
        with open(join(secret_dir, secret_file)) as secret_file:
            secrets = json.load(secret_file)
        status = 200
        logging.info("Secrets are loaded")
    except Exception as e:
        status = 500
        logging.error(f"Error loading secrets\n{str(e)}")

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
        open_pulls = {}
        avatar = app_configs['default_avatar']
        channel = app_configs['default_channel']
        github_token = secrets['github-auth']['Bearer-token']
        current_time = datetime.datetime.now()
        for repository in app_configs['repositories']:
            if channel in repository:
                channel = repository['channel']
            if avatar in repository:
                avatar = repository['avatar']

            print(f"{repository['name']} is checking")
            owner = repository['owner']
            repo = repository['name']
            open_pulls[repository['name']] = []
            url = f"https://api.github.com/repos/{owner}/{repo}/pulls"
            payload = {}
            headers = {
                'Authorization': f'Bearer {github_token}'
            }
            response = requests.request("GET", url, headers=headers, data=payload)

            for open_pull in response.json():
                if open_pull['state'] == 'open':
                    updated_time = datetime.datetime.strptime(open_pull['created_at'], "%Y-%m-%dT%H:%M:%SZ")
                    # Change here to check 3 days "current_time - datetime.timedelta(days=3) > updated_time"
                    if current_time - datetime.timedelta(days=3) < updated_time:
                        print(f"...{open_pull['title']} is checking")
                        open_pull_object = {}
                        open_pull_object["repo"] = f"{owner}/{repo}"
                        open_pull_object["webhook_url"] = secrets['webhook-channels'][channel]['url']
                        open_pull_object["avatar"] = avatar
                        open_pull_object["title"] = f"Pull request - {open_pull['title']} is {open_pull['state']}"
                        open_pull_object["user"] = {}
                        open_pull_object["user"]["name"] = open_pull['user']['login']
                        open_pull_object["user"]["url"] = open_pull['user']['html_url']
                        open_pull_object["details"] = open_pull['body']
                        open_pull_object["created"] = open_pull['created_at']
                        open_pull_object["updated"] = open_pull['updated_at']
                        open_pull_object["assignees"] = open_pull['assignees']
                        open_pull_object["url"] = open_pull['html_url']
                        open_pull_object["diff_url"] = open_pull['diff_url']
                        open_pull_object["head"] = {}
                        open_pull_object["head"]["repo"] = open_pull['head']['repo']['full_name']
                        open_pull_object["head"]["branch"] = open_pull['head']['ref']
                        open_pull_object["head"][
                            "url"] = f"{open_pull['head']['repo']['html_url']}/tree/{open_pull['head']['ref']}"
                        open_pull_object["base"] = {}
                        open_pull_object["base"]["repo"] = open_pull['base']['repo']['full_name']
                        open_pull_object["base"]["branch"] = open_pull['base']['ref']
                        open_pull_object["base"][
                            "url"] = f"{open_pull['base']['repo']['html_url']}/tree/{open_pull['base']['ref']}"

                        if len(open_pull['assignees']) > 0:
                            assignees = []
                            for assignee in open_pull['assignees']:
                                assignees.append(assignee['login'])
                            open_pull_object["assignees"] = assignees

                        if len(open_pull['requested_reviewers']) > 0:
                            reviewers = []
                            for reviewer in open_pull['requested_reviewers']:
                                reviewers.append(reviewer['login'])
                            open_pull_object["reviewers"] = reviewers

                        results = send_message(open_pull_object)

                        print(f"......{results}")


if __name__ == "__main__":
    main()

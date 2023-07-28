# Copyright 2023 The Oppia Authors. All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the 'License');
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an 'AS-IS' BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""The file to trigger the workflow to send pending-review notifications."""

from __future__ import annotations

import argparse
import logging
import os
import re

from typing import List, Optional
from src import github_domain
from src import github_services


PARSER = argparse.ArgumentParser(
    description='Send pending review notifications to reviewers.')
PARSER.add_argument(
    '--token',
    type=str,
    help='The github-token to be used for creating comment in GitHub discussion.')
PARSER.add_argument(
    '--repo',
    type=str,
    help='The repository for fetching the pull requests.')
PARSER.add_argument(
    '--category',
    type=str,
    help='The category name of the discussion.')
PARSER.add_argument(
    '--title',
    type=str,
    help='The title of the discussion.')
PARSER.add_argument(
    '--max-wait-hours',
    type=int,
    help='The maximum time in hour to wait for a review. Any PR exceed that limit should'
        'be considered to notify the reviewer.')
PARSER.add_argument(
    '--verbose',
    action='store_true',
    help='Whether to add important logs in the process.')

TEMPLATE_PATH = '.github/PENDING_REVIEW_NOTIFICATION_TEMPLATE.md'


def generate_message(username: str, pr_list: str, template_path: str=TEMPLATE_PATH) -> str:
    """Generates message using the template provided in
    PENDING_REVIEW_NOTIFICATION_TEMPLATE.md.

    Args:
        username: str. Reviewer username.
        pr_list: str. List of PRs not reviewed within the maximum waiting time.
        template_path: str. The template file path.

    Returns:
        str. The generated message.

    Raises:
        Exception. Template file is missing in the given path.
    """
    if not os.path.exists(template_path):
        raise Exception(f'Please add a template file at: {template_path}')
    message = ''
    with open(template_path, 'r', encoding='UTF-8') as file:
        message = file.read()

    message = re.sub(r'\{\{ *username *\}\}', '@' + username, message)
    message = re.sub(r'\{\{ *pr_list *\}\}', pr_list, message)

    return message


def send_notification(
    username: str,
    pull_requests: List[github_domain.PullRequest],
    org_name: str,
    repo_name: str,
    discussion_category: str,
    discussion_title: str
) -> None:
    """Sends notification on github-discussion.

    Args:
        username: str. GitHub username of the reviewer.
        pull_requests: List. List of pending PRs.
        org_name: str. The GitHub org name.
        repo_name: str. The GitHub repo name.
        discussion_category: str. Category name of the discussion.
        discussion_title: str. Discussion title.
    """
    pr_list_messages: List[str] = []
    for pull_request in pull_requests:
        assignee = pull_request.get_assignee(username)
        assert assignee is not None
        pr_list_messages.append(
            f'- [#{pull_request.number}]({pull_request.url}) [Waiting for the '
            f'last {assignee.get_waiting_time()}]')

    message = generate_message(username, '\n'.join(pr_list_messages), TEMPLATE_PATH)

    github_services.create_discussion_comment(
        org_name, repo_name, discussion_category, discussion_title, message)


def main(args: Optional[List[str]]=None) -> None:
    """The main function to execute the workflow.

    Args:
        args: list. A list of arguments to parse.

    Raises:
        Exception. All required arguments not provided.
    """
    parsed_args = PARSER.parse_args(args=args)

    org_name, repo_name = parsed_args.repo.split('/')
    discussion_category = parsed_args.category
    discussion_title = parsed_args.title
    max_wait_hours = parsed_args.max_wait_hours

    # Raise error if any of the required arguments are not provided.
    required_args = ['max_wait_hours', 'discussion_category', 'discussion_title']
    for arg in required_args:
        if arg is None:
            raise Exception(f'Please provide {arg} argument.')

    if parsed_args.verbose:
        logging.basicConfig(
            format='%(levelname)s: %(message)s', level=logging.INFO)

    github_services.init_service(parsed_args.token)

    reviewer_to_assigned_prs = github_services.get_prs_assigned_to_reviewers(
        org_name, repo_name, max_wait_hours)
    for reviewer_name, prs in reviewer_to_assigned_prs.items():
        send_notification(
            reviewer_name, prs, org_name, repo_name, discussion_category, discussion_title)


if __name__ == '__main__':
    main()

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

"""GitHub related commands and functions."""

from __future__ import annotations

import collections
import datetime
import logging

from typing import Any, Callable, DefaultDict, Dict, List, Optional, Union
from dateutil import parser
import requests
from src import github_domain



_TOKEN = None
GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'
PULL_REQUESTS_URL_TEMPLATE = 'https://api.github.com/repos/{0}/{1}/pulls'
ISSUE_TIMELINE_URL_TEMPLATE = (
    'https://api.github.com/repos/{0}/{1}/issues/{2}/timeline')


def init_service(token: Optional[str]=None) -> None:
    """Initialize service with the given token.

    Args:
        token: str|None. The GitHub token or None if no token is given.

    Raises:
        Exception. Given GitHub token is not valid.
    """
    if token is None or token == '':
        raise Exception('Must provide a valid GitHub Personal Access Token.')

    global _TOKEN # pylint: disable=global-statement
    _TOKEN = token


# Here we use type Any because the decorated function can take any number of arguments
# of any type and return a value of any type.
def check_token(func: Callable[..., Any]) -> Callable[..., Any]:
    """A decorator to check whether the service is initialized with
    the token or not.
    """

    # Here we use type Any because the function can take any number of arguments of any
    # type and return a value of any type.
    def execute_if_token_initialized(*args: Any, **kwargs: Any) -> Any:
        """Executes the given function if the token is initialized."""
        if _TOKEN is None:
            raise Exception(
                'Initialize the service with github_services.init_service(TOKEN).')
        return func(*args, **kwargs)

    return execute_if_token_initialized


def _get_request_headers() -> Dict[str, str]:
    """Returns the request headers for github-request."""

    return {
        'Accept': 'application/vnd.github.v3+json',
        'Authorization': f'token {_TOKEN}'
    }


@check_token
def get_prs_assigned_to_reviewers(
    org_name: str,
    repository: str,
    max_waiting_time: int
) -> DefaultDict[str, List[github_domain.PullRequest]]:
    """Fetches all PRs and returns a list of PRs assigned to reviewers.

    Args:
        org_name: str. GitHub organization name.
        repository: str. GitHub repository name.
        max_waiting_time: int. The maximum time in hour to wait for a review. Any PR
            exceed that limit should be considered to notify the reviewer.

    Returns:
        dict. A dictionary that represents the reviewer and the PRs, the reviewer
        is assigned to.
    """

    pr_url = PULL_REQUESTS_URL_TEMPLATE.format(org_name, repository)
    reviewer_to_assigned_prs: (
        DefaultDict[str, List[github_domain.PullRequest]]) = (
        collections.defaultdict(list))

    page_number = 1
    while True:
        logging.info('Fetching Pull requests')
        params: Dict[str, Union[str, int]] = {
            'page': page_number, 'per_page': 100, 'status': 'open'
        }
        response = requests.get(
            pr_url,
            params=params,
            headers=_get_request_headers(),
            timeout=15
        )
        response.raise_for_status()
        pr_subset = response.json()

        if len(pr_subset) == 0:
            break
        page_number += 1

        pull_requests = [
            github_domain.PullRequest.from_github_response(pull_request)
            for pull_request in pr_subset]
        update_assignee_timestamp(org_name, repository, pull_requests)
        for pull_request in pull_requests:
            if not pull_request.is_reviewer_assigned():
                continue
            for reviewer in pull_request.assignees:
                # Since a reviewer was assigned, we are not expecting the respective
                # timestamp(when the the reviewer was assigned) to be none.
                assert reviewer.assigned_on_timestamp is not None
                pending_review_time = (
                    datetime.datetime.now(datetime.timezone.utc) -
                    reviewer.assigned_on_timestamp)
                if (reviewer.username != pull_request.author_username) and (
                    pending_review_time >=
                    datetime.timedelta(hours=max_waiting_time)
                ):
                    reviewer_to_assigned_prs[reviewer.username].append(pull_request)
    return reviewer_to_assigned_prs


# Here we use type Any because the response we get from the api call is hard
# to annotate in a typedDict.
def __process_activity(
    pull_request: github_domain.PullRequest,
    event: Dict[str, Any]
) -> None:
    """Process activity and update the respective timestamp when the assignee was assigned."""
    if event['event'] != 'assigned':
        return

    assignee = pull_request.get_assignee(event['assignee']['login'])
    event_timestamp = parser.parse(event['created_at'])

    # If a reviewer is not assigned, the `assigned_on_timestamp` value will be None. The
    # following code is checking that condition before setting the timestamp.
    if assignee:
        if assignee.assigned_on_timestamp:
            assignee.set_assigned_on_timestamp(
                max([assignee.assigned_on_timestamp, event_timestamp]))
        else:
            assignee.set_assigned_on_timestamp(event_timestamp)


def update_assignee_timestamp(
    org_name: str,
    repository: str,
    pr_list: List[github_domain.PullRequest]
) -> None:
    """Fetches PR timeline and updates assignment timestamp."""
    for pull_request in pr_list:
        pr_number = pull_request.number
        activity_url = ISSUE_TIMELINE_URL_TEMPLATE.format(
            org_name, repository, pr_number)

        page_number = 1
        while True:
            logging.info('Fetching PR #%s timeline', pr_number)
            response = requests.get(
                activity_url,
                params={'page': page_number, 'per_page': 100},
                headers={
                    'Accept': 'application/vnd.github+json',
                    'Authorization': f'token {_TOKEN}'},
                timeout=15
            )
            response.raise_for_status()
            timeline_subset = response.json()

            if len(timeline_subset) == 0:
                break

            for event in timeline_subset:
                __process_activity(pull_request, event)

            page_number += 1


@check_token
def create_discussion_comment(
    org_name: str,
    repo_name: str,
    discussion_category: str,
    discussion_title: str,
    message: str
) -> None:
    """Comment in the existing GitHub discussion."""

    # The following query is written in GraphQL and is being used to fetch data about the
    # existing GitHub discussions. This helps to find out the discussion where we want
    # to comment. To learn more, check this out https://docs.github.com/en/graphql.
    query = """
        query ($org_name: String!, $repository: String!) {
            repository(owner: $org_name, name: $repository) {
                discussionCategories(first: 10) {
                    nodes {
                        id
                        name
                        repository {
                            id
                            discussions(last: 10) {
                                edges {
                                    node {
                                        id
                                        title
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    """

    variables = {
        'org_name': org_name,
        'repository': repo_name
    }

    response = requests.post(
        GITHUB_GRAPHQL_URL,
        json={'query': query, 'variables': variables},
        headers=_get_request_headers(),
        timeout=15
    )
    data = response.json()

    discussion_id = None
    discussion_categories = (
        data['data']['repository']['discussionCategories']['nodes'])

    for category in discussion_categories:
        if category['name'] == discussion_category:
            discussions = category['repository']['discussions']['edges']
            for discussion in discussions:
                if discussion['node']['title'] == discussion_title:
                    discussion_id = discussion['node']['id']
                    break
            if discussion_id is None:
                raise Exception(
                    f'Discussion with title {discussion_title} not found, please create a '
                    'discussion with that title.')
            break

    if discussion_id is None:
        raise Exception(f'{discussion_category} category is missing in GitHub Discussion.')

    # The following code is written in GraphQL and is being used to perform a mutation
    # operation. More specifically, we are using it to comment in GitHub discussion to
    # let reviewers know about some of their pending tasks. To learn more, check this out
    # https://docs.github.com/en/graphql.
    query = """
        mutation comment($discussion_id: ID!, $comment: String!) {
            addDiscussionComment(input: {discussionId: $discussion_id, body: $comment}) {
                clientMutationId
                comment {
                    id
                }
            }
        }
    """

    variables = {
        'discussion_id': discussion_id,
        'comment': message
    }

    response = requests.post(
        GITHUB_GRAPHQL_URL,
        json={'query': query, 'variables': variables},
        headers=_get_request_headers(),
        timeout=15
    )
    response.raise_for_status()

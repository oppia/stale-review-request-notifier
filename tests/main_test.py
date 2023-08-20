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

"""Unit test for the main.py file."""

from __future__ import annotations

import builtins
import datetime
import json
import unittest
from unittest import mock

from src import github_services
from src import main

import requests
import requests_mock
from typing import Any, Dict, List


class GenerateMessageTests(unittest.TestCase):
    """Test generate message function."""

    def setUp(self) -> None:
        self.test_template = '{{ username }}\n{{ pr_list }}'

    def test_generate_message(self) -> None:
        """Test generate message function."""

        file_data = mock.mock_open(read_data=self.test_template)
        template_path = '.github/PENDING_REVIEW_NOTIFICATION_TEMPLATE.md'
        with mock.patch('builtins.open', file_data):
            pr_list = (
                '- [#123](https://githuburl.pull/123) [Waiting for the last 2 days, 8'
                ' hours]')
            response = main.generate_message('reviewerName1', pr_list, template_path)
        expected_response = (
            '@reviewerName1\n- [#123](https://githuburl.pull/123) [Waiting for the last 2'
            ' days, 8 hours]')
        self.assertEqual(expected_response, response)

    def test_generate_message_raises_template_not_found_error(self) -> None:
        """Test generate message function."""

        file_data = mock.mock_open(read_data=self.test_template)
        template_path = 'invalid_path'
        with mock.patch('builtins.open', file_data):
            pr_list = (
                '- [#123](https://githuburl.pull/123) [Waiting for the last 2 days, 8 '
                'hours]')
            with self.assertRaisesRegex(
                builtins.BaseException, f'Please add a template file at: {template_path}'):
                main.generate_message('reviewerName1', pr_list, template_path)


class ModuleIntegrationTest(unittest.TestCase):
    """Integration test for the send notification feature."""

    def _get_past_time(self, hours: int=0) -> str:
        """Returns the subtraction of current time and the arg passed in hours."""
        return (
            datetime.datetime.now(
                datetime.timezone.utc) - datetime.timedelta(hours=hours)).strftime(
                '%Y-%m-%dT%H:%M:%SZ')

    def setUp(self) -> None:
        self.org_name = 'orgName'
        self.repo_name = 'repo'
        self.discussion_category = 'category'
        self.discussion_title = 'title'
        self.response_for_get_categories = {
            "data": {
                "repository": {
                    "discussionCategories": {
                        "nodes": [
                            {
                                "id": "test_category_id_1",
                                "name": "test_category_name_1"
                            },
                            {
                                "id": "test_category_id_2",
                                "name": "test_category_name_2"
                            }
                        ]
                    }
                }
            }
        }
        self.response_for_get_discussion = {
            'data': {
                'repository': {
                    'discussions': {
                        'nodes': [
                            {
                                'id': 'test_discussion_id_1',
                                'title': 'test_discussion_title_1',
                                'number': 12345
                            }
                        ]
                    }
                }
            }
        }
        self.response_for_get_old_comment_ids = {
            'data': {
                'repository': {
                    'discussion': {
                        'comments': {
                            'nodes': [
                                {
                                    'id': 'test_comment_id_2',
                                    'createdAt': '2022-05-05T11:44:00Z'
                                }
                            ]
                        }
                    }
                }
            }
        }
        self.response_for_delete_comment = {
            'data': {
                'deleteDiscussionComment': {
                    'clientMutationId': 'test_id'
                }
            }
        }
        # Here we use type Any because this response is hard to annotate in a typedDict.
        self.response_for_post_comment: Dict[str, Any] = {
            'data': {
                'addDiscussionComment': {
                    'clientMutationId': 'test_id',
                    'comment': {
                        'id': 'test_discussion_id_1'
                    }
                }
            }
        }
        # Here we use type Any because this response is hard to annotate in a typedDict.
        self.pull_response: List[Dict[str, Any]] = [{
            'html_url': 'https://githuburl.pull/123',
            'number': 123,
            'title': 'PR title 1',
            'user': {
                'login': 'authorName',
            },
            'assignees': [{
                'login': 'reviewerName1',
            }, {
                'login': 'reviewerName2',
            }]
        }, {
            'html_url': 'https://githuburl.pull/234',
            'number': 234,
            'title': 'PR title 2',
            'user': {
                'login': 'authorName',
            },
            'assignees': [{
                'login': 'reviewerName1',
            }, {
                'login': 'reviewerName2',
            }]
        }]
        self.timeline1 = [{
            'event': 'created'
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName1'
            },
            'created_at': self._get_past_time(hours=22)
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName2'
            },
            'created_at': self._get_past_time(hours=56)
        }]

        self.timeline2 = [{
            'event': 'created'
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName1'
            },
            'created_at': self._get_past_time(hours=23)
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName2'
            },
            'created_at': self._get_past_time(hours=19)
        }]
        self.test_template = '{{ username }}\n{{ pr_list }}'

    def mock_all_get_requests(self, mock_request: requests_mock.Mocker) -> None:
        """Mock all get requests."""

        param_page_1 = '?page=1&per_page=100'
        param_page_2 = '?page=2&per_page=100'
        mock_request.get(
            github_services.PULL_REQUESTS_URL_TEMPLATE.format(
                self.org_name, self.repo_name) + param_page_1,
            text=json.dumps(self.pull_response))
        mock_request.get(
            github_services.PULL_REQUESTS_URL_TEMPLATE.format(
                self.org_name, self.repo_name) + param_page_2,
            text=json.dumps([]))

        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.org_name, self.repo_name, 123) + param_page_1,
            text=json.dumps(self.timeline1))
        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.org_name, self.repo_name, 123) + param_page_2,
            text=json.dumps([]))

        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.org_name, self.repo_name, 234) + param_page_1,
            text=json.dumps(self.timeline2))
        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.org_name, self.repo_name, 234) + param_page_2,
            text=json.dumps([]))

    # Here we use type Any because this response is hard to annotate in a typedDict.
    def mock_post_requests(self, response: Dict[str, Any]) -> mock.Mock:
        """Mock post requests."""

        mocked_response = mock.Mock()
        mocked_response.json.return_value = response
        return mocked_response

    def test_executing_main_function_sends_notification(self) -> None:
        """Test main function to send notification."""

        # Here we are mocking the POST requests that we will use in the test below.
        # and they are listed in the particular order they will be called.
        post_requests_side_effect: List[mock.Mock] = [
            self.mock_post_requests(self.response_for_get_categories),
            self.mock_post_requests(self.response_for_get_discussion),
            self.mock_post_requests(self.response_for_get_old_comment_ids),
            self.mock_post_requests(self.response_for_delete_comment),
            self.mock_post_requests(self.response_for_get_categories),
            self.mock_post_requests(self.response_for_get_discussion),
            self.mock_post_requests(self.response_for_post_comment),
            self.mock_post_requests(self.response_for_get_categories),
            self.mock_post_requests(self.response_for_get_discussion),
            self.mock_post_requests(self.response_for_post_comment)
        ]

        with requests_mock.Mocker() as mock_request:

            self.mock_all_get_requests(mock_request)

            # Here we are patching the POST requests using side_effect. So, when we put
            # callables inside `side_effect`, it will iterate through the items and
            # return each at a time. For our test, we are expecting total 12 POST requests.
            # 7 requests from the `main` function call and 5 requests from the below calls
            # to assert the response.
            with mock.patch(
                'requests.post', side_effect=(
                    post_requests_side_effect + post_requests_side_effect
            )) as mock_post:

                self.assertEqual(mock_request.call_count, 0)
                self.assertEqual(mock_post.call_count, 0)

                file_data = mock.mock_open(read_data=self.test_template)
                with mock.patch('builtins.open', file_data):
                    main.main([
                        '--repo', 'orgName/repo',
                        '--category', 'test_category_name_1',
                        '--title', 'test_discussion_title_1',
                        '--max-wait-hours', '20',
                        '--token', 'githubTokenForApiRequest'
                    ])

                response_for_get_categories = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))
                response_for_get_discussion = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))
                response_for_get_old_comment_ids = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))
                response_for_delete_comment = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))
                response_for_get_categories = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))
                response_for_get_discussion = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))
                response_for_post_comment = requests.post(
                    github_services.GITHUB_GRAPHQL_URL, timeout=(
                        github_services.TIMEOUT_SECS))

        self.assertEqual(mock_post.call_count, 17)
        self.assertEqual(mock_request.call_count, 6)

        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_get_categories.json.return_value, self.response_for_get_categories)  # type: ignore[attr-defined]
        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_get_discussion.json.return_value, self.response_for_get_discussion)  # type: ignore[attr-defined]
        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_get_old_comment_ids.json.return_value, self.response_for_get_old_comment_ids)  # type: ignore[attr-defined]
        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_delete_comment.json.return_value, self.response_for_delete_comment)  # type: ignore[attr-defined]
        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_get_categories.json.return_value, self.response_for_get_categories)  # type: ignore[attr-defined]
        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_get_discussion.json.return_value, self.response_for_get_discussion)  # type: ignore[attr-defined]
        # Here we use MyPy ignore because the response is of Mock type and
        # Mock does not contain return_value attribute, so because of this MyPy throws an
        # error. Thus to avoid the error, we used ignore here.
        self.assertEqual(
            response_for_post_comment.json.return_value, self.response_for_post_comment)  # type: ignore[attr-defined]

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

"""Unit test for the index.py file."""

import unittest
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import patch, mock_open
import requests_mock

from src import index
from src import github_services


class ModuleIntegrationTest(unittest.TestCase):
    """Integration test for the send notification feature."""
    def setUp(self):
        self.orgName = 'orgName'
        self.repoName = 'repo'
        self.discussion_category = 'category'
        self.discussion_title = 'title'
        self.query_discussion_id = """
            query ($org_name: String!, $repository: String!) {
                repository(owner: $org_name, name: $repository) {
                    discussionCategories(first: 10) {
                        nodes {
                            id
                            name
                            repository {
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

        self.variables = {
            'org_name': self.orgName,
            'repository': self.repoName
        }
        self.response_for_discussions = {
            "data": {
                "repository": {
                    "discussionCategories": {
                        "nodes": [
                            {
                                "id": "test_category_id_1",
                                "name": "test_category_name_1",
                                "repository": {
                                    "discussions": {
                                        "edges": [
                                            {
                                                "node": {
                                                "id": "test_discussion_id_1",
                                                "title": "test_discussion_title_1"
                                                }
                                            }
                                        ]
                                    }
                                }
                            },
                            {
                                "id": "test_category_id_2",
                                "name": "test_category_name_2",
                                "repository": {
                                    "discussions": {
                                        "edges": [
                                            {
                                                "node": {
                                                "id": "test_discussion_id_2",
                                                "title": "test_discussion_title_2"
                                                }
                                            }
                                        ]
                                    }
                                }
                            }
                        ]
                    }
                }
            }
        }

        self.response_for_comment = {
            "data": {
                "addDiscussionComment": {
                    "clientMutationId": 'test_id',
                    "comment": {
                        "id": "test_discussion_id_1"
                    }
                }
            }
        }


        self.pull_response =  [{
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
        def get_past_time(hours=0):
            return (
                datetime.now(timezone.utc) - timedelta(hours=hours)).strftime(
                    "%Y-%m-%dT%H:%M:%SZ")
        self.timeline1 = [{
            'event': 'created'
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName1'
            },
            'created_at': get_past_time(hours=22)
        },{
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName2'
            },
            'created_at': get_past_time(hours=56)
        }]

        self.timeline2 = [{
            'event': 'created'
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName1'
            },
            'created_at': get_past_time(hours=23)
        }, {
            'event': 'assigned',
            'assignee': {
                'login': 'reviewerName2'
            },
            'created_at': get_past_time(hours=19)
        }]

        self.test_template = "{{ username }}\n{{ pr_list }}"

    def mock_all_get_requests(self, mock_request):
        param_page_1='?page=1&per_page=100'
        param_page_2='?page=2&per_page=100'
        mock_request.get(
            github_services.PULL_REQUESTS_URL_TEMPLATE.format(
                self.orgName, self.repoName) + param_page_1,
            text=json.dumps(self.pull_response))
        mock_request.get(
            github_services.PULL_REQUESTS_URL_TEMPLATE.format(
                self.orgName, self.repoName) + param_page_2,
            text=json.dumps([]))

        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.orgName, self.repoName, 123) + param_page_1,
            text=json.dumps(self.timeline1))
        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.orgName, self.repoName, 123) + param_page_2,
            text=json.dumps([]))

        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.orgName, self.repoName, 234) + param_page_1,
            text=json.dumps(self.timeline2))
        mock_request.get(
            github_services.ISSUE_TIMELINE_URL_TEMPLATE.format(
                self.orgName, self.repoName, 234) + param_page_2,
            text=json.dumps([]))


    @patch('requests.post')
    def mock_post_discussion_request(self, mock_request):
        """Mock the API response made for fetching discussion data."""

        mock_request.return_value = self.response_for_discussions
        result = github_services.get_discussions(self.orgName, self.repoName)

        return result

    @patch('requests.post')
    def mock_post_comment_request(self, mock_request):
        """Mock the API response made for comment."""

        mock_request.return_value = self.response_for_comment
        result = github_services.post_comment('test_discussion_id_1', 'random')

        return result

    def test_executing_main_function_sends_notification(self):
        with requests_mock.Mocker() as mock_request:
            self.mock_all_get_requests(mock_request)
            request_1 = self.mock_post_discussion_request(mock_request)
            request_2 = self.mock_post_comment_request(mock_request)
            file_data = mock_open(read_data=self.test_template)
            with patch("builtins.open", file_data):
                index.main([
                    '--repo', 'orgName/repo',
                    '--category', 'category',
                    '--title', 'title',
                    '--max-wait-hours', '20',
                    '--token', 'githubTokenForApiRequest'
                ])
        self.assertTrue(request_1.called)
        self.assertTrue(request_1.call_count, 1)

        

        self.assertTrue(request_2.called)
        self.assertEqual(request_2.call_count, 2)
        expected_messages = [
            {
                'body': '@reviewerName1\n- [#123](https://githuburl.pull/123) '
                    '[Waiting from the last 22 hours]\n'
                    '- [#234](https://githuburl.pull/234) '
                    '[Waiting from the last 23 hours]'
            },
            {
                'body': '@reviewerName2\n- [#123](https://githuburl.pull/123) '
                    '[Waiting from the last 2 days, 8 hours]'
            },
        ]
        self.assertEqual(
            request_2.request_history[0].json(), expected_messages[0])
        self.assertEqual(
            request_2.request_history[1].json(), expected_messages[1])

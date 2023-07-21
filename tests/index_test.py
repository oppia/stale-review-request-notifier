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
from unittest.mock import patch, mock_open, Mock
import requests_mock
import requests
from typing import Dict, Any
from src import index
from src import github_services


class GenerateMessageTests(unittest.TestCase):
    """test generate message function."""

    def test_generate_message(self):
        
        self.test_template = "{{ username }}\n{{ pr_list }}"
        file_data = mock_open(read_data=self.test_template)
        with patch("builtins.open", file_data):
            pr_list = '- [#123](https://githuburl.pull/123) [Waiting for the last 2 days, 8 hours]'
            response = index.generate_message('reviewerName1', pr_list)
        mocked_response = ('@reviewerName1\n'
            '- [#123](https://githuburl.pull/123) [Waiting for the last 2 days, 8 hours]')
        self.assertEqual(mocked_response, response)
   

class ModuleIntegrationTest(unittest.TestCase):
    """Integration test for the send notification feature."""
    def setUp(self):
        self.orgName = 'orgName'
        self.repoName = 'repo'
        self.discussion_category = 'category'
        self.discussion_title = 'title'
        self.response_for_discussions: Dict[str, Any] = {
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
        self.response_for_comment: Dict[str, Any] = {
            "data": {
                "addDiscussionComment": {
                    "clientMutationId": 'test_id',
                    "comment": {
                        "id": "test_discussion_id_1"
                    }
                }
            }
        }
        self.pull_response: List[Dict[str, Any]] =  [{
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
        def get_past_time(hours: int=0) -> str:
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

    def mock_all_get_requests(self, mock_request: requests_mock) -> None:
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

    def test_executing_main_function_sends_notification(self) -> None:
        with requests_mock.Mocker() as mock_request:
            self.mock_all_get_requests(mock_request)
                
            mock_resp_1 = Mock()
            mock_resp_1.json.return_value = self.response_for_discussions

            mock_resp_2 = Mock()
            mock_resp_2.json.return_value = self.response_for_comment
            with patch("requests.post", side_effect=[
                mock_resp_1 if i % 2 == 0 else mock_resp_2 for i in range(6)]) as mock_post:

                request_1 = requests.post(github_services.GITHUB_GRAPHQL_URL)
                request_2 = requests.post(github_services.GITHUB_GRAPHQL_URL)
                file_data = mock_open(read_data=self.test_template)
                with patch("builtins.open", file_data):
                    index.main([
                        '--repo', 'orgName/repo',
                        '--category', 'test_category_name_1',
                        '--title', 'test_discussion_title_1',
                        '--max-wait-hours', '20',
                        '--token', 'githubTokenForApiRequest'
                    ])
        self.assertTrue(request_1, self.response_for_discussions)
        self.assertTrue(request_2, self.response_for_comment)

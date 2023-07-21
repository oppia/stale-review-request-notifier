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

"""Unit test for the github_services.py file."""

from __future__ import annotations

import unittest
import collections
from datetime import datetime, timedelta, timezone
import json
from unittest.mock import patch, Mock
import requests_mock
import requests
from typing import Any, Dict, List
from src import github_services, github_domain


class TestInitServices(unittest.TestCase):

    def test_init_service_with_token(self):
        token = 'my_github_token'
        github_services.init_service(token)
        self.assertEqual(github_services._TOKEN, token)

    def test_init_service_without_token(self):
        with self.assertRaises(Exception):
            github_services.init_service()

    def test_init_service_with_empty_token(self):
        with self.assertRaises(Exception):
            github_services.init_service('')


class TestGetPrsAssignedToReviewers(unittest.TestCase):

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

    def test_get_prs_assigned_to_reviewers(self):
        token = 'my_github_token'
        github_services.init_service(token)

        with requests_mock.Mocker() as mock_request:
            self.mock_all_get_requests(mock_request)
            
            response = github_services.get_prs_assigned_to_reviewers(
                self.orgName, self.repoName, 20)

        self.assertEqual(mock_request.call_count, 6)
    
    def test_create_discussion_comment(self):
        """test create discussion comment."""

        token = 'my_github_token'
        github_services.init_service(token)
        with requests_mock.Mocker() as mock_requests:
            self.mock_all_get_requests(mock_requests)

            mock_resp_1 = Mock()
            mock_resp_1.json.return_value = self.response_for_discussions
            mock_resp_2 = Mock()
            mock_resp_2.json.return_value = self.response_for_comment

            with patch('requests.post', side_effect=[
                mock_resp_1, mock_resp_2, mock_resp_1, mock_resp_2]) as mock_post:

                github_services.create_discussion_comment(
                    self.orgName,
                    self.repoName,
                    'test_category_name_1',
                    'test_discussion_title_1',
                    'test_message'
                )
            
        self.assertTrue(mock_resp_1.assert_called)
        self.assertTrue(mock_resp_2.assert_called)
        self.assertEqual(mock_post.call_count, 2)

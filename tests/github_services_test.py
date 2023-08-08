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

import datetime
import json
import unittest
from unittest import mock
from dateutil.tz import tzutc

from src import github_services, github_domain

import requests_mock
from typing import Any, Dict, List


class TestInitServices(unittest.TestCase):
    """Test init service."""

    def test_init_service_with_token(self) -> None:

        token = 'my_github_token'
        github_services.init_service(token)
        self.assertEqual(github_services._TOKEN, token)

    def test_init_service_without_token(self) -> None:

        with self.assertRaises(Exception):
            github_services.init_service()

    def test_init_service_with_empty_token(self) -> None:

        with self.assertRaises(Exception):
            github_services.init_service('')


class TestGetPrsAssignedToReviewers(unittest.TestCase):
    """Test get prs assigned to reviewers."""

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
        # Here we use type Any because this response is hard to annotate in a typedDict.
        self.response_for_get_discussion_data: Dict[str, Any] = {
            'data': {
                'repository': {
                    'discussionCategories': {
                        'nodes': [
                            {
                                'id': 'test_category_id_1',
                                'name': 'test_category_name_1',
                                'repository': {
                                    'discussions': {
                                        'edges': [
                                            {
                                                'node': {
                                                'id': 'test_discussion_id_1',
                                                'title': 'test_discussion_title_1',
                                                'number': 1
                                                }
                                            }
                                        ]
                                    }
                                }
                            },
                            {
                                'id': 'test_category_id_2',
                                'name': 'test_category_name_2',
                                'repository': {
                                    'discussions': {
                                        'edges': [
                                            {
                                                'node': {
                                                'id': 'test_discussion_id_2',
                                                'title': 'test_discussion_title_2',
                                                'number': 2
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

    def test_get_pull_request_object_from_dict(self) -> None:

        token = 'my_github_token'
        github_services.init_service(token)
        mocked_response = {
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
        }
        # Here we use type Any because this response is hard to annotate in a typedDict.
        expected_response_dict: Dict[str, Any] = {
            'html_url': 'https://githuburl.pull/123',
            'number': 123, 'title': 'PR title 1',
            'user': {'login': 'authorName'},
            'assignees': [
                {
                    'login': 'reviewerName1',
                    'created_at': datetime.datetime(
                        2023, 7, 31, 22, 24, 38, tzinfo=tzutc())
                },
                {
                    'login': 'reviewerName2',
                    'created_at': datetime.datetime(
                        2023, 7, 30, 12, 24, 38, tzinfo=tzutc())
                }
            ]
        }

        with requests_mock.Mocker() as mock_request:
            self.assertEqual(mock_request.call_count, 0)
            self.mock_all_get_requests(mock_request)
            response = github_services.get_pull_request_object_from_dict(
                self.org_name, self.repo_name, mocked_response
            )
        self.assertEqual(mock_request.call_count, 2)
        self.assertIsInstance(response, github_domain.PullRequest)
        self.assertEqual(response.url, expected_response_dict['html_url'])
        self.assertEqual(response.pr_number, expected_response_dict['number'])
        self.assertEqual(response.title, expected_response_dict['title'])
        self.assertEqual(
            response.author_username, expected_response_dict['user']['login'])

    def test_get_prs_assigned_to_reviewers(self) -> None:
        token = 'my_github_token'
        github_services.init_service(token)

        with requests_mock.Mocker() as mock_request:
            self.assertEqual(mock_request.call_count, 0)
            self.mock_all_get_requests(mock_request)

            github_services.get_prs_assigned_to_reviewers(
                self.org_name, self.repo_name, 20)

        self.assertEqual(mock_request.call_count, 6)

    def test_get_discussion_data(self) -> None:
        """Test _get_discussion_data."""

        mock_response = mock.Mock()
        mock_response.json.return_value = self.response_for_get_discussion_data
        self.assertTrue(mock_response.assert_not_called)

        with requests_mock.Mocker() as mock_requests:

            self.mock_all_get_requests(mock_requests)

            with mock.patch('requests.post', side_effect=[mock_response]) as mock_post:

                mocked_response = github_services._get_discussion_data(
                    self.org_name,
                    self.repo_name,
                    'test_category_name_1',
                    'test_discussion_title_1'
                )
        self.assertTrue(mock_response.assert_called_once)
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(mocked_response, ('test_discussion_id_1', 1))

    def test_get_old_comment_ids(self) -> None:
        """Test _get_old_comment_ids."""

        mock_response = mock.Mock()
        mock_response.json.return_value = self.response_for_get_old_comment_ids
        self.assertTrue(mock_response.assert_not_called)

        with requests_mock.Mocker() as mock_requests:

            self.mock_all_get_requests(mock_requests)

            with mock.patch('requests.post', side_effect=[mock_response]) as mock_post:

                mocked_response = github_services._get_old_comment_ids(
                    self.org_name,
                    self.repo_name,
                    1
                )
        self.assertTrue(mock_response.assert_called_once)
        self.assertEqual(mock_post.call_count, 1)
        self.assertEqual(mocked_response, ['test_comment_id_2'])

    def test_delete_comment(self) -> None:
        """Test delete_comment."""

        token = 'my_github_token'
        github_services.init_service(token)

        mock_response = mock.Mock()
        mock_response.json.return_value = self.response_for_delete_comment
        self.assertTrue(mock_response.assert_not_called)

        with requests_mock.Mocker() as mock_requests:

            self.mock_all_get_requests(mock_requests)

            with mock.patch('requests.post', side_effect=[mock_response]) as mock_post:

                github_services._delete_comment('test_comment_id_2')
        self.assertTrue(mock_response.assert_called)
        self.assertEqual(mock_post.call_count, 1)

    def test_post_comment(self) -> None:
        """Test post comment."""

        mock_response = mock.Mock()
        mock_response.json.return_value = self.response_for_post_comment
        self.assertTrue(mock_response.assert_not_called)

        with requests_mock.Mocker() as mock_requests:

            self.mock_all_get_requests(mock_requests)

            with mock.patch('requests.post', side_effect=[mock_response]) as mock_post:

                github_services._post_comment(
                    'test_discussion_id_1',
                    'test_message'
                )
        self.assertTrue(mock_response.assert_called_once)
        self.assertEqual(mock_post.call_count, 1)

    def test_delete_discussion_comments(self) -> None:
        """Test delete_discussion_comments function."""

        token = 'my_github_token'
        github_services.init_service(token)

        mock_response_1 = mock.Mock()
        mock_response_1.json.return_value = self.response_for_get_discussion_data

        mock_response_2 = mock.Mock()
        mock_response_2.json.return_value = self.response_for_get_old_comment_ids

        mock_response_3 = mock.Mock()
        mock_response_3.json.return_value = self.response_for_delete_comment

        self.assertTrue(mock_response_1.assert_not_called)
        self.assertTrue(mock_response_2.assert_not_called)
        self.assertTrue(mock_response_3.assert_not_called)

        with requests_mock.Mocker() as mock_requests:

            self.mock_all_get_requests(mock_requests)

            with mock.patch('requests.post', side_effect=[
                mock_response_1, mock_response_2, mock_response_3]) as mock_post:

                github_services.delete_discussion_comments(
                    self.org_name,
                    self.repo_name,
                    'test_category_name_1',
                    'test_discussion_title_1'
                )
        self.assertTrue(mock_response_1.assert_called)
        self.assertTrue(mock_response_2.assert_called)
        self.assertTrue(mock_response_3.assert_called)
        self.assertEqual(mock_post.call_count, 3)

    def test_add_discussion_comments(self) -> None:
        """Test discussion comments."""

        token = 'my_github_token'
        github_services.init_service(token)

        mock_response_1 = mock.Mock()
        mock_response_1.json.return_value = self.response_for_get_discussion_data

        mock_response_2 = mock.Mock()
        mock_response_2.json.return_value = self.response_for_post_comment

        self.assertTrue(mock_response_1.assert_not_called)
        self.assertTrue(mock_response_2.assert_not_called)

        with requests_mock.Mocker() as mock_requests:

            self.mock_all_get_requests(mock_requests)

            with mock.patch('requests.post', side_effect=[
                mock_response_1, mock_response_2]) as mock_post:

                github_services.add_discussion_comments(
                    self.org_name,
                    self.repo_name,
                    'test_category_name_1',
                    'test_discussion_title_1',
                    'test_message'
                )
        self.assertTrue(mock_response_1.assert_called)
        self.assertTrue(mock_response_2.assert_called)
        self.assertEqual(mock_post.call_count, 2)

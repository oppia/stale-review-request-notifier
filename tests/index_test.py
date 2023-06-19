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

from __future__ import annotations

import unittest
from datetime import datetime, timedelta, timezone
import json

from src import github_services


class ModuleIntegrationTest(unittest.TestCase):
    """Integration test for the send notification feature."""
    def setUp(self):
        self.orgName = 'orgName'
        self.repoName = 'repo'
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

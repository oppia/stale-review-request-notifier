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

"""Unit test for the github_domain.py file."""

from __future__ import annotations

import datetime
import unittest

from src import github_domain


class AssigneeDomainUnitTest(unittest.TestCase):
    """Assignee class test."""

    def test_constructor_creates_object(self) -> None:

        assignee = github_domain.Assignee('username', datetime.datetime(1, 1, 1))
        self.assertIsInstance(assignee, github_domain.Assignee)
        self.assertEqual(assignee.username, 'username')
        self.assertEqual(assignee.assigned_on_timestamp, datetime.datetime(1, 1, 1))


class PullRequestDomainUnitTest(unittest.TestCase):
    """PullRequest class test."""

    def test_constructor_creates_object_with_correct_value(self) -> None:

        reviewers = [
            github_domain.Assignee(
                'username', assigned_on_timestamp=datetime.datetime(1, 1, 1))]
        pull_request = github_domain.PullRequest(
            'https://example.com', 123, 'authorName', 'PR title', reviewers)

        self.assertIsInstance(pull_request, github_domain.PullRequest)
        self.assertEqual(pull_request.url, 'https://example.com')
        self.assertEqual(pull_request.pr_number, 123)
        self.assertEqual(pull_request.author_username, 'authorName')
        self.assertEqual(pull_request.title, 'PR title')
        self.assertEqual(pull_request.assignees, reviewers)

    def test_get_assignee_with_invalid_username_returns_none(self) -> None:

        reviewers = [
            github_domain.Assignee(
                'username', assigned_on_timestamp=datetime.datetime(1, 1, 1))]
        pull_request = github_domain.PullRequest(
            'https://example.com', 123, 'authorName', 'PR title', reviewers)

        self.assertEqual(
            pull_request.get_assignee('username'), reviewers[0])
        self.assertEqual(
            pull_request.get_assignee('invalidName'), None)

    def test_is_reviewer_assigned_for_non_reviewers(self) -> None:

        reviewers = [
            github_domain.Assignee(
                'authorName', assigned_on_timestamp=datetime.datetime(1, 1, 1))]
        pull_request = github_domain.PullRequest(
            'https://example.com', 123, 'authorName', 'PR title', reviewers)

        self.assertFalse(pull_request.is_reviewer_assigned())

    def test_is_reviewer_assigned_for_assigned_reviewers(self) -> None:

        reviewers = [
            github_domain.Assignee(
                'reviewer', assigned_on_timestamp=datetime.datetime(1, 1, 1))]
        pull_request = github_domain.PullRequest(
            'https://example.com', 123, 'authorName', 'PR title', reviewers)

        self.assertTrue(pull_request.is_reviewer_assigned())

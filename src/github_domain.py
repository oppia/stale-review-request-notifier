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

"""Domain objects for github entities."""

from __future__ import annotations

import datetime

from typing import Any, Dict, List, Optional, Type


class Assignee:
    """A class representing an assignee of a pull request."""

    def __init__(
        self,
        username: str,
        assigned_on_timestamp: Optional[datetime.datetime] = None
    ) -> None:
        """
        Args:
            username: str. GitHub username of the assignee.
            assigned_on_timestamp: datetime|None. The time when the reviewer was
                assigned, else None.
        """
        self.username = username
        self.assigned_on_timestamp = assigned_on_timestamp

    def set_assigned_on_timestamp(self, assigned_on_timestamp: datetime.datetime) -> None:
        """Sets timestamp to assignee.

        Args:
            assigned_on_timestamp: datetime. The time when the reviewer was
                assigned to the PR.
        """
        self.assigned_on_timestamp = assigned_on_timestamp

    def get_waiting_time(self) -> str:
        """Returns the waiting time on review.
        The waiting time is the difference between the current time and the time when the
        reviewer was assigned to the PR.

        Returns:
            str. The waiting time in days and hours.
        """

        # Since a reviewer was assigned, we are not expecting the respective
        # timestamp (when the reviewer was assigned) to be none.
        assert self.assigned_on_timestamp is not None
        delta = datetime.datetime.now(datetime.timezone.utc) - self.assigned_on_timestamp
        days = delta.days
        hours, _ = divmod(delta.seconds, 3600)
        waiting_time = []
        if days:
            waiting_time.append(f'{days} day{"s" if days > 1 else ""}')

        if hours:
            waiting_time.append(f'{hours} hour{"s" if hours > 1 else ""}')

        return ', '.join(waiting_time)

    def __repr__(self) -> str:
        return f'@{self.username} assigned on {self.assigned_on_timestamp}'


class PullRequest:
    """A class representing a pull request on GitHub."""

    def __init__(
        self,
        url: str,
        number: int,
        author_username: str,
        title: str,
        assignees: List[Assignee]
    ) -> None:
        """Constructs a PullRequest object.

        Args:
            url: str. The url of the PR.
            number: int. The PR number.
            author_username: str. GitHub username of the PR Author.
            title: str. PR title.
            assignees: List(Assignee). List of assignees.
        """
        self.url = url
        self.number = number
        self.author_username = author_username
        self.title = title
        self.assignees = assignees

    def is_reviewer_assigned(self) -> bool:
        """Checks whether a reviewer is assigned to the PR.

        Returns:
            bool. A boolean value representing whether a reviewer is assigned or not.
        """
        return not (
            len(self.assignees) == 0 or (
            len(self.assignees) == 1 and self.assignees[0].username == self.author_username))

    def get_assignee(self, user: str) -> Optional[Assignee]:
        """Returns the assignee object for the given user if it exists.

        Returns:
            Assignee|None. Returns the assignee object if anyone is assigned, or None if
            no one is assigned.
        """
        assignee = next(filter(lambda x: x.username == user, self.assignees), None)
        return assignee

    def __repr__(self) -> str:
        return f'PR #{self.number} by {self.author_username}'

    # Here we use type Any because the response we get from the api call
    # is hard to annotate in a typedDict.
    @classmethod
    def from_github_response(
        cls: Type[PullRequest],
        pr_dict: Dict[str, Any]
    ) -> PullRequest:
        """Create the object using the pull_request response."""
        assignees_dict = pr_dict['assignees']
        assignees = [Assignee(a['login']) for a in assignees_dict]

        pull_request = cls(
            url=pr_dict['html_url'],
            number=pr_dict['number'],
            title=pr_dict['title'],
            author_username=pr_dict['user']['login'],
            assignees=assignees
        )
        return pull_request

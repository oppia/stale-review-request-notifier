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

"""Github related commands and functions."""

from __future__ import annotations

import collections
import datetime
import logging

from send_review_notification import github_domain

from dateutil import parser
import requests
from typing import Any, Callable, DefaultDict, Dict, List, Optional, Union

_TOKEN = None
GITHUB_GRAPHQL_URL = 'https://api.github.com/graphql'
PULL_REQUESTS_URL_TEMPLATE = 'https://api.github.com/repos/{0}/{1}/pulls'
ISSUE_TIMELINE_URL_TEMPLATE = (
    'https://api.github.com/repos/{0}/{1}/issues/{2}/timeline')
CREATE_DISCUSSION_URL_TEMPLATE = (
    'https://api.github.com/orgs/{0}/teams/{1}/discussions')


def init_service(token: Optional[str]=None) -> None:
    """Initialize service with the given token."""
    if token is None:
        raise Exception('Must provide Github Personal Access Token.')

    global _TOKEN # pylint: disable=global-statement
    _TOKEN = token

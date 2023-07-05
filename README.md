# `stale-review-request-notifier` GitHub Action

Action to send notifications to reviewers on github-discussion when they miss reviewing PRs within expected time.

## Table of Contents

* [Usage](#usage)
* [Inputs](#inputs)

## Usage
1. [Generate a github-personal-access-token](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token) with rights to create discussion and read issues & pull request.
![image](https://user-images.githubusercontent.com/16653571/137939909-08edfe36-8bb3-475a-ad51-f2f2d4861da4.png)
![image](https://user-images.githubusercontent.com/16653571/137939045-c3b73543-81fb-410c-895a-73753344f901.png)

2. [Create a new repository secret](https://docs.github.com/en/actions/security-guides/encrypted-secrets#creating-encrypted-secrets-for-a-repository) (assuming DISCUSSION_NOTIFICATION_TOKEN) with value as the newly generated personal access token.

3. Create a GitHub discussion and then a workflow file in the `.github/workflows/` dir.

    **Example:**
    ```yaml
    name: Send pending review notifications to reviewer on github-discussion
    on:
      schedule:
        - cron: '0 0 * * 2,4'

    jobs:
      send_notifications:
        name: Send pending review notifications
        runs-on:  ${{ matrix.os }}
        strategy:
          matrix:
            os: [ubuntu-22.04]
        steps:
          - uses: actions/checkout@v3
          - uses: actions/setup-python@v4
            with:
              python-version: '3.8.15'
              architecture: 'x64'
          - uses: oppia/stale-review-request-notifier
            with:
              category-name: << category_name >>
              discussion-title: << discussion_title >>
              repo-token: ${{ secrets.DISCUSSION_NOTIFICATION_TOKEN }}
              review-turnaround-hours: << TURNAROUND_HOURS >>
    ```
    **Important notes:**
      - Replace `<< category_name >>` and `<< discussion_title >>` with the respective category name and discussion title.
      - Replace `<< TURNAROUND_HOURS >>` with the expected PR review time.
      - Don't use space in `category_name` or `discussion_title`; otherwise, they will be considered different arguments.
      - The [POSIX cron syntax](https://pubs.opengroup.org/onlinepubs/9699919799/utilities/crontab.html#tag_20_25_07) needs to be quoted as * is a special character in YAML.

4. Add PENDING_REVIEW_NOTIFICATION_TEMPLATE.yml file in `.github/` dir.

   Example:
   ```
   Hi {{ username }},

   It looks like you haven't reviewed the following PRs within the expected time:
   {{ pr_list }}

   Can you please review the pending PRs as soon as possible?

   Please make sure to reply to this thread once all the PRs are reviewed!
   ```
     **Important notes:**
       - Template can have `username` and  `pr_list` placeholders which will eventually get replaced with the reviewer's username and the list of PRs waiting on their review respectively.

## Inputs

| Name          | Requirement | Default | Description |
| ------------- | ----------- | ------- | ----------- |
| `category-name`               | _required_  | | The category name the discussion belongs to.|
| `discussion-title`  | _required_  | | The title of the discussion in which comments will be posted.
| `repo-token`              | _required_  | | The github-personal-token which at least have rights to create a discussion in the given team. |
| `review-turnaround-hours` | _required_  | | The maximum review turnaround hours. Notifications will be sent only for PRs waiting for more than review-turnaround-hours.|

## Known issue

The `secret.GITHUB_TOKEN` available in build container doesn't have permission to create discussion in team.

## License

See [LICENSE](LICENSE).

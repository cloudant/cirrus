"""
tests for github_tools
"""

from unittest import TestCase, mock

from cirrus import configuration
from cirrus import github_tools

from .harnesses import _repo_directory


def mock_load_configuration():
    """
    Return a Configuration object populated with the basics, without reading
    the config file from disk.
    """
    config_content = {
        'github': {
            'api_base': 'https://API-BASE'
        },
        'package': {
            'description': 'cirrus development and build git extensions',
            'name': 'testrepo',
            'organization': 'testorg',
            'python_versions': '3',
            'version': '3.1.2',
            'version_file': 'src/cirrus/__init__.py'
        }
    }
    c = configuration.Configuration('config_file')
    c.update(config_content)
    return c


class GithubToolsTest(TestCase):
    """
    _GithubToolsTest_
    """
    def setUp(self):
        """
        setup mocks
        """
        config = mock_load_configuration()
        self.owner = config.organisation_name()
        self.repo = config.package_name()
        self.release = '0.0.0'
        self.commit_info = [
            {
                'committer': 'bob',
                'message': 'I made a commit!',
                'date': '2014-08-28'},
            {
                'committer': 'tom',
                'message': 'toms commit',
                'date': '2014-08-27'}]

        self.patch_get = mock.patch('cirrus.github_tools.requests.get')
        self.mock_get = self.patch_get.start()

        self.mock_load_configuration = mock.patch(
            'cirrus.github_tools.load_configuration'
        ).start()
        self.mock_load_configuration.return_value = config

    def tearDown(self):
        """
        teardown mocks
        """
        mock.patch.stopall()

    @mock.patch('cirrus.github_tools.get_active_branch')
    @mock.patch('cirrus.github_tools.requests.post')
    def test_create_pull_request(self, mock_post, mock_get_branch):
        """
        _test_create_pull_request_
        """
        resp_json = {
            'html_url': 'https://github.com/{org}/{repo}/pull/1'.format(
                org=self.owner,
                repo=self.repo
            )
        }

        mock_resp = mock.Mock()
        mock_resp.raise_for_status.return_value = False
        mock_resp.json.return_value = resp_json
        mock_post.return_value = mock_resp
        result = github_tools.create_pull_request(
            self.repo,
            {'title': 'Test', 'body': 'This is a test'},
            'token')
        self.assertTrue(self.mock_load_configuration.called)
        self.assertTrue(mock_get_branch.called)
        self.assertTrue(mock_post.called)
        self.assertEqual(result, resp_json['html_url'])

    def test_get_releases(self):
        """
        _test_get_releases_
        """
        resp_json = [
            {
             'tag_name': self.release
             }
                     ]
        mock_req = mock.Mock()
        mock_req.raise_for_status.return_value = False
        mock_req.json.return_value = resp_json
        self.mock_get.return_value = mock_req
        result = github_tools.get_releases(self.owner, self.repo, 'token')
        self.assertTrue(self.mock_get.called)
        self.assertIn('tag_name', result[0])

    @mock.patch('cirrus.github_tools.load_configuration')
    @mock.patch("cirrus.github_tools.requests.post")
    @mock.patch("cirrus.github_tools.push")
    def test_current_branch_mark_status(self, mock_push, mock_post, mock_config_load):
        """
        _test_current_branch_mark_status_

        """
        def check_post(url, headers, json=None):
            self.assertTrue(
                url.startswith(
                    "https://API-BASE/repos/testorg/testrepo/statuses/"
                )
            )
            self.assertEqual(json.get("state"), "success")
            self.assertTrue(json.get("description"))
            self.assertTrue(json.get("context"))
            return mock.Mock()

        mock_post.side_effect = check_post
        mock_config_load.return_value = mock_load_configuration()

        github_tools.current_branch_mark_status(_repo_directory(), "success")

        self.assertTrue(mock_post.called)
        self.assertTrue(mock_push.called)


class GitHubContextTest(TestCase):
    """Tests for GitHubContext methods using HTTP calls."""

    def setUp(self):
        self.mock_git = mock.patch('cirrus.github_tools.git').start()
        repo = mock.Mock()
        repo.active_branch.name = 'TEST_BRANCH'
        self.mock_git.Repo.return_value = repo

        self.mock_load_configuration = mock.patch(
            'cirrus.github_tools.load_configuration'
        ).start()
        self.mock_load_configuration.return_value = mock_load_configuration()

        session_patcher = mock.patch('cirrus.github_tools.requests.Session')

        self.session = mock.Mock(name='Session instance')

        mock_Session = session_patcher.start()
        mock_Session.return_value = self.session

    def tearDown(self):
        mock.patch.stopall()

    def test_api_base(self):
        self.assertEqual('https://API-BASE', github_tools._api_base())

    def test_constructor(self):
        with github_tools.GitHubContext('.') as gh:
            self.assertEqual('https://API-BASE', gh.api_base)
            self.assertEqual(
                'https://API-BASE/repos/testorg/testrepo',
                 gh.repository_api_base
            )

    def test_branch_state(self):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {'state': 'ok'}

        with github_tools.GitHubContext('.') as gh:
            gh.session.get.return_value = mock_resp
            gh.branch_state('BRANCH')
            gh.session.get.assert_called_with(
                'https://API-BASE/repos/testorg/testrepo/commits/BRANCH/status'
            )

    def test_branch_status_list(self):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = ['some status']

        with github_tools.GitHubContext('.') as gh:
            gh.session.get.return_value = mock_resp
            # its a generator
            next(gh.branch_status_list('BRANCH'))
            gh.session.get.assert_called_with(
                'https://API-BASE/repos/testorg/testrepo/commits/BRANCH/statuses'
            )

    @mock.patch('cirrus.github_tools.push')
    def test_set_branch_state(self, m_push):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {'state': 'ok'}
        mock_repo = mock.Mock()
        mock_repo.head.commit.hexsha = 'SHA'

        with github_tools.GitHubContext('.') as gh:
            gh.repo = mock_repo
            gh.session.post.return_value = mock_resp
            gh.set_branch_state(
                'success',
                'continuous-integration/travis-ci',
                branch='BRANCH'
            )
            gh.session.post.assert_called_with(
                'https://API-BASE/repos/testorg/testrepo/statuses/SHA',
                json={
                    'state': 'success',
                    'description': 'State after cirrus check.',
                    'context': 'continuous-integration/travis-ci'
                }
            )

        m_push.assert_called_with('.')

    @mock.patch('cirrus.github_tools.time')
    def test_wait_on_gh_status_success(self, m_time):
        # returns a state which is one of 'failure', 'pending', 'success'

        with github_tools.GitHubContext('.') as gh:
            gh.branch_state = mock.Mock(return_value='success')
            gh.wait_on_gh_status(branch_name='BRANCH')

        m_time.sleep.assert_not_called()

    @mock.patch('cirrus.github_tools.time')
    def test_wait_on_gh_status_failure(self, m_time):
        with github_tools.GitHubContext('.') as gh:
            gh.branch_state = mock.Mock(return_value='failure')
            with self.assertRaises(RuntimeError):
                gh.wait_on_gh_status(branch_name='BRANCH')

        m_time.sleep.assert_not_called()

    @mock.patch('cirrus.github_tools.time')
    def test_wait_on_gh_status_pending(self, m_time):
        # 'success' status breaks the wait loop
        with github_tools.GitHubContext('.') as gh:
            gh.branch_state = mock.Mock(
                side_effect=['pending', 'pending', 'success']
            )
            gh.wait_on_gh_status(branch_name='BRANCH', timeout=30, interval=2)
        m_time.sleep.assert_has_calls([mock.call(2), mock.call(2)])
        m_time.reset_mock()

        # The timeout limit breaks the loop when the state is stuck in 'pending'
        def _always_be_pending(*args):
            return 'pending'

        with github_tools.GitHubContext('.') as gh:
            gh.branch_state = mock.Mock(side_effect=_always_be_pending)

            with self.assertRaises(RuntimeError):
                gh.wait_on_gh_status(
                    branch_name='BRANCH',
                    timeout=10,
                    interval=2
                )

        # sleep should ben called 6 times to break the timeout threshold.
        # 5 iterations of 2s to reach timeout=10, one iteration to fail the
        # time_spent > timeout check.
        m_time.sleep.assert_has_calls([mock.call(2)] * 6)
        m_time.reset_mock()

        # 'failure' raises RuntimeError immediately
        with github_tools.GitHubContext('.') as gh:
            gh.branch_state = mock.Mock(side_effect='failure')

            with self.assertRaises(RuntimeError):
                gh.wait_on_gh_status(
                    branch_name='BRANCH',
                    timeout=10,
                    interval=2
                )

        m_time.assert_not_called()

    def test_pull_requests(self):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = [
            {'user': {'login': 'hodor'}, 'body': 'PR body'}
        ]

        with github_tools.GitHubContext('.') as gh:
            gh.session.get.return_value = mock_resp
            # Its a generator
            row = next(gh.pull_requests(user='hodor'))

        gh.session.get.assert_called_with(
            'https://API-BASE/repos/testorg/testrepo/pulls',
            params={'state': 'open'}
        )
        self.assertEqual({'user': {'login': 'hodor'}, 'body': 'PR body'}, row)

    def test_pull_request_details(self):
        mock_resp = mock.Mock()
        mock_resp.json.return_value = {'url': 'URL', 'id': 'ID'}

        with github_tools.GitHubContext('.') as gh:
            gh.session.get.return_value = mock_resp
            pr = gh.pull_request_details(123)

        gh.session.get.assert_called_with(
            'https://API-BASE/repos/testorg/testrepo/pulls/123'
        )
        self.assertEqual({'url': 'URL', 'id': 'ID'}, pr)

    def test_plus_one_pull_request(self):
        mock_resp = mock.Mock()

        # lifted from GH API docs
        pr_statuses_url = (
            'https://api.github.ibm.com/repos/testrepo/Hello-World/statuses/'
            '6dcb09b5b57875f334f61aebed695e2e4193db5e'
        )
        pr_data = {
            'statuses_url': pr_statuses_url,
            'user': {
                'login': 'homer'
            }
        }

        with github_tools.GitHubContext('.') as gh:
            gh.gh_user = 'smithers'
            gh.session.post.return_value = mock_resp
            gh.plus_one_pull_request(pr_id=123, pr_data=pr_data, context='+1')

        gh.session.post.assert_called_with(
            pr_statuses_url,
            json={
                'state': 'success',
                'description': 'Reviewed by smithers',
                'context': '+1',
            }
        )

    def test_review_pull_request(self):
        mock_resp = mock.Mock()
        # lifted from GH API docs
        pr_statuses_url = (
            'https://api.github.ibm.com/repos/testrepo/Hello-World/statuses/'
            '6dcb09b5b57875f334f61aebed695e2e4193db5e'
        )
        pr_issue_url = 'https://api.github.com/repos/testrepo/Hello-World/issues/1'
        pr_data = {
            'statuses_url': pr_statuses_url,
            'issue_url': pr_issue_url
        }

        with github_tools.GitHubContext('.') as gh:
            gh.session.post.return_value = mock_resp
            gh.plus_one_pull_request = mock.Mock()
            gh.pull_request_details = mock.Mock(return_value=pr_data)
            gh.review_pull_request(123, 'Comment', plusone=True)

        gh.pull_request_details.assert_called_with(123)
        gh.plus_one_pull_request.assert_called_with(
            context='+1',
            pr_data={
                'statuses_url': pr_statuses_url,
                'issue_url': pr_issue_url
            }
        )
        gh.session.post.assert_called_with(
            'https://api.github.com/repos/testrepo/Hello-World/issues/1/comments',
            json={'body': 'Comment'}
        )

import argparse
import pathlib
import re
import git
import jira


class RepoReader:
    _skip_patterns = [
        re.compile(r'^preparing development version.+', re.IGNORECASE),
        re.compile(r'^preparing hbase release.+', re.IGNORECASE),
        re.compile(r'^\s*updated? pom.xml version (for|to) .+', re.IGNORECASE),
        re.compile(r'^\s*updated? chang', re.IGNORECASE),
        re.compile(r'^\s*updated? (book|docs|documentation)', re.IGNORECASE),
        re.compile(r'^\s*updating (docs|changes).+', re.IGNORECASE),
        re.compile(r'^\s*bump (pom )?versions?', re.IGNORECASE),
        re.compile(r'^\s*updated? (version|poms|changes).+', re.IGNORECASE),
    ]
    _identify_leading_jira_id_patterns = [
        re.compile(r'^[\s\[]*(hbase-\d+)', re.IGNORECASE),
        re.compile(r'^[\s\[]*(hbse-\d+)', re.IGNORECASE),  # typo
        re.compile(r'^[\s\[]*(hbae-\d+)', re.IGNORECASE),  # typo
        re.compile(r'^[\s\[]*(hbase \d+)', re.IGNORECASE), # typo
    ]

    def __init__(self, repo):
        self._repo = git.Repo(pathlib.Path(repo).absolute())

    def merge_base(self, release_branch, previous_release_branch):
        commit = self._repo.merge_base(release_branch, previous_release_branch)
        if commit:
            return commit[0]
        raise Exception(f'can not find merge base for {release_branch} and {previous_release_branch}')

    @staticmethod
    def _skip(summary):
        return any([p.match(summary) for p in RepoReader._skip_patterns])

    @staticmethod
    def extract_leading_jira_id(commit):
        if RepoReader._skip(commit.summary):
            return None
        for pattern in RepoReader._identify_leading_jira_id_patterns:
            match = pattern.match(commit.summary)
            if match:
                return re.sub(r'HBSE-|HBAE-|HBASE ', 'HBASE-', match.groups()[0].upper())
        return None

    def get_jira_issues_from_commits(self, start_commit, end_commit):
        commits = list(self._repo.iter_commits(f'{start_commit}...{end_commit}'))
        num_commits = len(commits)
        print(f'there are {num_commits} commits from {start_commit} to {end_commit}')
        issues = []
        for commit in commits:
            issue = RepoReader.extract_leading_jira_id(commit)
            if issue:
                issues.append(issue)
        return issues


class JiraReader:
    def __init__(self, jira_url):
        self._jira = jira.JIRA(jira_url)

    @staticmethod
    def construct_jql(fix_versions):
        fix_versions_condition = ','.join(fix_versions)
        return f'project = HBase AND resolution = Fixed AND fixVersion IN ({fix_versions_condition})'

    def fetch_issues(self, fix_versions):
        start_at = 0
        max_results = 50
        jql = JiraReader.construct_jql(fix_versions)
        issues = []
        while True:
            issue_list = self._jira.search_issues(jql, start_at, max_results)
            issues.extend(issue.key for issue in issue_list)
            start_at += len(issue_list)
            if start_at >= issue_list.total:
                break
        return issues


def missed_issues_in_previous_release(issues_in_git_commits, issues_in_git_commits_previous_release,
                                      ignore_missing_in_current_release):
    print('Commit to previous release but not in current release:')
    for issue in sorted(filter(lambda i: i not in ignore_missing_in_current_release,
                               issues_in_git_commits_previous_release.difference(issues_in_git_commits))):
        print('\t' + issue)


def audit_jira_issues_and_git_commits(issues_in_jira, issues_in_git_commits, ignore_missing_in_git,
                                      ignore_missing_in_jira):
    print('Issues in jira but not in git commits:')
    for issue in sorted(filter(lambda i: i not in ignore_missing_in_git,
                               issues_in_jira.difference(issues_in_git_commits))):
        print('\t' + issue)
    print('Issues in git commits but not in jira:')
    for issue in sorted(filter(lambda i: i not in ignore_missing_in_jira,
                               issues_in_git_commits.difference(issues_in_jira))):
        print('\t' + issue)


def read_jira_issues_from_file(file):
    if file:
        with open(file) as f:
            return set(l.split()[0] for l in f.readlines())
    else:
        return set()


def build_arg_parser():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '--release-versions',
        help='Comma separated list of release versions',
        required=True)
    parser.add_argument(
        '--previous-release-version',
        help='Previous release version',
        required=True)
    parser.add_argument(
        '--release-branch',
        help='Git branch for current release',
        required=True)
    parser.add_argument(
        '--previous-release-branch',
        help='Git branch for the previous release',
        required=True)
    parser.add_argument(
        '--repo',
        help='Local git repository directory',
        required=True)
    parser.add_argument(
        '--ignore-missing-in-current-release',
        help='A file contains the jira issues which should be ignored when checking jira issue in previous release but not in current release',
        required=False
    )
    parser.add_argument(
        '--ignore-missing-in-git',
        help='A file contains the jira issues which should be ignored when checking jira issues in jira ifx versions but not in git commits',
        required=False
    )
    parser.add_argument(
        '--ignore-missing-in-jira',
        help='A file contains the jira issues which should be ignored when checking jira issues in git commits but not in jira fix versions',
        required=False
    )
    return parser


if __name__ == '__main__':
    parser = build_arg_parser()
    args = parser.parse_args()
    repo = RepoReader(args.repo)
    merge_base = repo.merge_base(args.release_branch, args.previous_release_branch)
    issues_in_git_commits = set(repo.get_jira_issues_from_commits(merge_base, args.release_branch))
    issues_in_git_commits_previous_release = set(
        repo.get_jira_issues_from_commits(merge_base, 'rel/' + args.previous_release_version))
    ignore_missing_in_current_release = read_jira_issues_from_file(args.ignore_missing_in_current_release)
    missed_issues_in_previous_release(issues_in_git_commits, issues_in_git_commits_previous_release,
                                      ignore_missing_in_current_release)

    jira = JiraReader('https://issues.apache.org/jira')
    issues_in_jira = set(jira.fetch_issues(args.release_versions))
    ignore_missing_in_git = read_jira_issues_from_file(args.ignore_missing_in_git)
    ignore_missing_in_jira = set(ignore_missing_in_current_release)
    audit_jira_issues_and_git_commits(issues_in_jira,
                                      issues_in_git_commits.difference(issues_in_git_commits_previous_release),
                                      ignore_missing_in_git, ignore_missing_in_jira)

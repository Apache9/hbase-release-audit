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
        re.compile(r'^[\s\[]*(hbse-\d+)', re.IGNORECASE), # typo
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
                return match.groups()[0].upper().replace('HBSE', 'HBASE')
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

def missed_issues_in_previous_release(issues_in_git_commits, issues_in_git_commits_previous_release):
    print('Commit to previous release but not in current release:')
    for issue in sorted(issues_in_git_commits_previous_release.difference(issues_in_git_commits)):
        print('\t' + issue)

def audit_jira_issues_and_git_commits(issues_in_jira, issues_in_git_commits):
    print('Issues in jira but not in git commits:')
    for issue in issues_in_jira.difference(issues_in_git_commits):
        print('\t' + issue)
    print('Issues in git commits but not in jira:')
    for issue in issues_in_git_commits.difference(issues_in_jira):
        print('\t' + issue)

if __name__ == '__main__':
    repo = RepoReader('/home/zhangduo/hbase/hbase')
    merge_base = repo.merge_base('origin/branch-3', 'origin/branch-2.0')
    issues_in_git_commits = set(repo.get_jira_issues_from_commits(merge_base, 'origin/branch-3'))
    issues_in_git_commits_previous_release = set(repo.get_jira_issues_from_commits(merge_base, 'rel/2.0.0'))
    missed_issues_in_previous_release(issues_in_git_commits, issues_in_git_commits_previous_release)

    jira = JiraReader('https://issues.apache.org/jira')
    issues_in_jira = set(jira.fetch_issues(['3.0.0-alpha-1, 3.0.0-alpha-2, 3.0.0-alpha-3, 3.0.0-alpha-4, 3.0.0-beta-1', '3.0.0-beta-2']))
    audit_jira_issues_and_git_commits(issues_in_jira, issues_in_git_commits.difference(issues_in_git_commits_previous_release))

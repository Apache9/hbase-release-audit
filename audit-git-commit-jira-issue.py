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

if __name__ == '__main__':
    repo = RepoReader('/home/zhangduo/hbase/hbase')
    merge_base = repo.merge_base('origin/branch-3', 'origin/branch-2.0')
    release_branch_issues = set(repo.get_jira_issues_from_commits(merge_base, 'origin/branch-3'))
    previous_release_branch_issues = repo.get_jira_issues_from_commits(merge_base, 'rel/2.0.0')
    previous_release_branch_issues.sort()
    for issue in previous_release_branch_issues:
        if issue not in release_branch_issues:
            print(issue)

import pathlib

import git


class RepoReader:
    def __init__(self, repo):
        self._repo = git.Repo(pathlib.Path(repo).absolute())

    def merge_base(self, release_branch, previous_release_branch):
        commit = self._repo.merge_base(release_branch, previous_release_branch)
        if commit:
            return commit[0]
        raise Exception(f'can not find merge base for {release_branch} and {previous_release_branch}')

    def get_jira_issues_from_commits(self, start_commit, end_commit):
        commits = list(self._repo.iter_commits(f'{start_commit}...{end_commit}'))
        num_commits = len(commits)
        print(f'there are {num_commits} commits from {start_commit} to {end_commit}')

if __name__ == '__main__':
    repo = RepoReader('/home/zhangduo/hbase/hbase')
    merge_base = repo.merge_base('origin/branch-3', 'origin/branch-2.0')
    repo.get_jira_issues_from_commits(merge_base, 'origin/branch-3')
    repo.get_jira_issues_from_commits(merge_base, 'rel/2.0.0')

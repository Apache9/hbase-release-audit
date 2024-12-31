# Example
```console
python3 audit-git-commit-jira-issue.py --release-versions "3.0.0-alpha-1,3.0.0-alpha-2,3.0.0-alpha-3,3.0.0-alpha-4,3.0.0-beta-1,3.0.0-beta-2" --previous-release-version 2.0.0 --release-branch branch-3 --previous-release-branch branch-2.0 --repo <local_repo_path> --ignore-missing-in-current-release 3.0.0/ignore-missing-in-current-release --ignore-missing-in-git 3.0.0/ignore-missing-in-git --ignore-missing-in-jira 3.0.0/ignore-missing-in-jira
```

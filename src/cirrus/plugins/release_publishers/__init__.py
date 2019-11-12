from .base import ReleaseInfoExtractor
from .github_issue import GitHubIssueReleaseInfoExtractor

def get_plugin(name):
    if name == 'github_issue':
        return GitHubIssueReleaseInfoExtractor
    # maybe just raise as this shouldn't be used directly
    return ReleaseInfoExtractor

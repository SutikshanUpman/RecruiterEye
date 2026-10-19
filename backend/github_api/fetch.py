from github import Github, Auth
from backend.core.config import GITHUB_TOKEN

gh = Github(auth=Auth.Token(GITHUB_TOKEN))

def get_repos(username):
    user = gh.get_user(username)
    repos = []
    for repo in user.get_repos():
        if not repo.fork:
            repos.append({"name": repo.name, "url": repo.html_url})
    return repos

if __name__ == "__main__":
    for r in get_repos("SutikshanUpman"):
        print(r)

"""
This function takes username and GitHubToken to fetch repos of that user with url
"""
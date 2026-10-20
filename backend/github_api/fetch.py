from github import Github, Auth, GithubException
from backend.core.config import GITHUB_TOKEN

gh = Github(auth=Auth.Token(GITHUB_TOKEN))


def get_repos(username):
    """This function takes username and GitHubToken to fetch repos of that user with url"""
    user = gh.get_user(username)
    repos = []
    for repo in user.get_repos():
        if not repo.fork:
            repos.append({"name": repo.name, "url": repo.html_url})
    return repos


def get_readme(username, repo_name):
    """Returns the README text of a repo, or "" if it has none."""
    try:
        repo = gh.get_repo(f"{username}/{repo_name}")
        return repo.get_readme().decoded_content.decode("utf-8")
    except GithubException:
        return ""

def get_structure(username, repo_name):
    """Returns a list of all file paths in a repo, e.g. ["backend/main.py", ...]."""
    try:
        repo = gh.get_repo(f"{username}/{repo_name}")
        tree = repo.get_git_tree(repo.default_branch, recursive=True)
        return [item.path for item in tree.tree if item.type == "blob"]
    except GithubException:
        return []

def get_commits(username, repo_name, limit=30):
    """Returns the latest commits as [{"message": ..., "date": ...}]."""
    try:
        repo = gh.get_repo(f"{username}/{repo_name}")
        commits = []
        for c in repo.get_commits()[:limit]:
            commits.append({
                "message": c.commit.message.split("\n")[0],
                "date": c.commit.author.date.isoformat(),
            })
        return commits
    except GithubException:
        return []

if __name__ == "__main__":
    for r in get_repos("SutikshanUpman"):
        commits = get_commits("SutikshanUpman", r["name"])
        print(r["name"], "->", len(commits), "commits")
    print(get_commits("SutikshanUpman", "recruitereye")[:3])
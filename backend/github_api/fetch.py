import time
import requests
from github import Github, Auth, GithubException
from backend.core.errors import ReviewError

gh = None


def get_github():
    global gh
    if gh is None:
        from backend.core.config import GITHUB_TOKEN

        if not GITHUB_TOKEN:
            raise ReviewError("GitHub is not configured on the server.", 503)
        gh = Github(auth=Auth.Token(GITHUB_TOKEN), timeout=15, retry=0)
    return gh


def get_repos(username: str) -> list[dict]:
    """This function takes username and GitHubToken to fetch repos of that user with url"""
    user = get_github().get_user(username)
    repos = []
    for repo in user.get_repos():
        if not repo.fork:
            repos.append({"name": repo.name, "url": repo.html_url})
    return repos


def get_pinned(username: str) -> list[dict]:
    """Returns the user's pinned repos as [{"name": ..., "url": ...}]."""
    from backend.core.config import GITHUB_TOKEN

    if not GITHUB_TOKEN:
        raise ReviewError("GitHub is not configured on the server.", 503)
    query = """
    query($login: String!) {
      user(login: $login) {
        pinnedItems(first: 6, types: REPOSITORY) {
          nodes { ... on Repository { name url owner { login } } }
        }
      }
    }
    """
    response = requests.post(
        "https://api.github.com/graphql",
        json={"query": query, "variables": {"login": username}},
        headers={"Authorization": f"Bearer {GITHUB_TOKEN}"},
        timeout=15,
    )
    response.raise_for_status()
    try:
        data = response.json()
        if data.get("errors"):
            errors = data["errors"]
            if any(e.get("type") == "RATE_LIMITED" for e in errors):
                raise ReviewError("GitHub rate limit reached. Please try again later.", 503)
            if any(e.get("type") == "NOT_FOUND" for e in errors):
                raise ReviewError("GitHub user not found.", 404)
            raise ReviewError("GitHub could not fetch pinned repositories.")
        user = data["data"]["user"]
        if user is None:
            raise ReviewError("GitHub user not found.", 404)
        nodes = user["pinnedItems"]["nodes"]
        if not isinstance(nodes, list):
            raise ValueError("Invalid pinned repositories")
        return [
            {"name": node["name"], "url": node["url"]}
            for node in nodes
            if node["owner"]["login"].lower() == username.lower()
        ]
    except (ValueError, KeyError, TypeError, AttributeError) as exc:
        raise ReviewError("GitHub returned an invalid profile response.") from exc


def get_readme(username: str, repo_name: str) -> str:
    """Returns the README text of a repo, or "" if it has none."""
    repo = get_github().get_repo(f"{username}/{repo_name}")
    try:
        return repo.get_readme().decoded_content.decode("utf-8")
    except GithubException as exc:
        if exc.status == 404:
            return ""
        raise
    except UnicodeDecodeError:
        return ""


def get_structure(username: str, repo_name: str) -> list[str]:
    """Returns a list of all file paths in a repo, e.g. ["backend/main.py", ...]."""
    repo = get_github().get_repo(f"{username}/{repo_name}")
    try:
        tree = repo.get_git_tree(repo.default_branch, recursive=True)
        return [item.path for item in tree.tree if item.type == "blob"]
    except GithubException as exc:
        if exc.status == 409:
            return []
        raise


def get_commits(username: str, repo_name: str, limit: int = 30) -> list[dict]:
    """Returns the latest commits as [{"message": ..., "date": ...}]."""
    repo = get_github().get_repo(f"{username}/{repo_name}")
    try:
        commits = []
        for c in repo.get_commits()[:limit]:
            commits.append({
                "message": c.commit.message.split("\n")[0],
                "date": c.commit.author.date.isoformat(),
            })
        return commits
    except GithubException as exc:
        if exc.status == 409:
            return []
        raise


def get_file(username: str, repo_name: str, path: str, limit: int = 2000) -> str:
    """Returns the first `limit` characters of one file, or "" if it can't be read."""
    repo = get_github().get_repo(f"{username}/{repo_name}")
    try:
        return repo.get_contents(path).decoded_content.decode("utf-8")[:limit]
    except GithubException as exc:
        if exc.status == 404:
            return ""
        raise
    except UnicodeDecodeError:
        return ""
    

def fetch_profile(username: str) -> list[dict]:
    """Returns one dict per repo, with readme, structure and commits filled in."""
    repos = get_pinned(username) or get_repos(username)
    for repo in repos:
        repo["readme"] = get_readme(username, repo["name"])
        repo["structure"] = get_structure(username, repo["name"])
        repo["commits"] = get_commits(username, repo["name"])
    return repos


if __name__ == "__main__":
    start = time.time()
    data = fetch_profile("SutikshanUpman")
    for r in data:
        print(r["name"], "|", len(r["readme"]), "chars |", len(r["structure"]), "files |", len(r["commits"]), "commits")
    print(len(data), "repos in", round(time.time() - start), "seconds")

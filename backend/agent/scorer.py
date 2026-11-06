import json
from backend.agent.llm import ask_llm

JUNK = ("__pycache__", ".ipynb_checkpoints", "node_modules", ".DS_Store")


def summarize_commits(commits: list[dict]) -> str:
    """Turns the commit list into one short line of facts."""
    if not commits:
        return "no commits"
    dates = sorted(c["date"][:10] for c in commits)
    messages = "; ".join(c["message"] for c in commits[:15])
    return f"{len(commits)} latest commits between {dates[0]} and {dates[-1]}. Messages: {messages}"


def clean_structure(paths: list[str]) -> list[str]:
    """Drops junk files and keeps at most 50 paths."""
    kept = [p for p in paths if not any(j in p for j in JUNK)]
    return kept[:50]


def score_repo(repo: dict) -> dict:
    """Asks the cheap LLM to rate a repo from 1 to 10 on three things."""
    prompt = (
        "You are a recruiter reviewing a GitHub repo. Rate each item from 1 to 10.\n"
        "- commit_history: steady, meaningful commits over time (not one upload, not messages like 'update')\n"
        "- structure: organised folders, config, tests, looks like a real project\n"
        "- readme: explains what it does and how to run it, clear\n"
        'Reply with JSON only, no other text, like: {"commit_history": 7, "structure": 5, "readme": 8}\n\n'
        f"Repo: {repo['name']}\n"
        f"Commits: {summarize_commits(repo['commits'])}\n"
        f"Files: {', '.join(clean_structure(repo['structure']))}\n"
        f"README (first 1500 chars): {repo['readme'][:1500]}"
    )
    reply = ask_llm(prompt)
    start, end = reply.find("{"), reply.rfind("}") + 1
    try:
        return json.loads(reply[start:end])
    except json.JSONDecodeError:
        return {}


def score_all(repos: list[dict]) -> list[dict]:
    """Adds scores and a total to each repo, returns repos sorted best first."""
    for repo in repos:
        scores = score_repo(repo)
        repo["scores"] = scores
        repo["total"] = sum(v for v in scores.values() if isinstance(v, (int, float)))
    return sorted(repos, key=lambda r: r["total"], reverse=True)


if __name__ == "__main__":
    from backend.github_api.fetch import fetch_profile
    from backend.agent.keywords import get_keywords
    from backend.agent.filter import filter_repos

    repos = fetch_profile("SutikshanUpman")
    keywords = get_keywords("AI Engineer working with Python, FastAPI, RAG, LLMs, Docker")
    for r in score_all(filter_repos(repos, keywords)):
        print(r["total"], r["name"], r["scores"])
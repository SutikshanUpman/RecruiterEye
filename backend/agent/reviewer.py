from backend.agent.llm import ask_llm, HEAVY_MODEL
from backend.agent.scorer import summarize_commits, clean_structure
from backend.github_api.fetch import get_file

CODE_EXT = (".py", ".js", ".ts", ".java", ".cpp", ".go")
SKIP = ("test", "__init__", "setup", "config")


def pick_top(repos, n=2):
    """Picks the n best repos using quality (total) and job fit (relevance)."""
    top_rel = max((r.get("relevance", 0) for r in repos), default=0) or 1

    def combined(r):
        return 0.6 * r.get("total", 0) / 30 + 0.4 * r.get("relevance", 0) / top_rel

    return sorted(repos, key=combined, reverse=True)[:n]


def pick_code_files(paths, n=3):
    """Picks up to n source files, shallow ones first."""
    code = [p for p in paths if p.endswith(CODE_EXT) and not any(s in p.lower() for s in SKIP)]
    code.sort(key=lambda p: p.count("/"))
    return code[:n]


def review_repo(username, repo):
    """Asks the heavy LLM for a recruiter-style review of one repo."""
    files = pick_code_files(repo["structure"])
    code = "\n\n".join(f"--- {p} ---\n{get_file(username, repo['name'], p)}" for p in files)
    prompt = (
        "You are a senior technical recruiter reviewing a candidate's GitHub repo "
        "for an AI engineering role. Be honest and specific, no flattery.\n"
        "Write under 250 words in exactly three parts:\n"
        "1. What a recruiter would notice first\n"
        "2. Red flags\n"
        "3. Top 3 fixes, most important first\n"
        "If no code is shown below, say the review is based on README and structure only.\n\n"
        f"Repo: {repo['name']}\n"
        f"Scores (1-10): {repo.get('scores', {})}\n"
        f"Commits: {summarize_commits(repo['commits'])}\n"
        f"Files: {', '.join(clean_structure(repo['structure']))}\n"
        f"README (first 1000 chars): {repo['readme'][:1000]}\n\n"
        f"Code:\n{code or '(none)'}"
    )
    return ask_llm(prompt, HEAVY_MODEL)


if __name__ == "__main__":
    from backend.github_api.fetch import fetch_profile
    from backend.agent.keywords import get_keywords
    from backend.agent.filter import filter_repos
    from backend.agent.scorer import score_all

    repos = fetch_profile("SutikshanUpman")
    keywords = get_keywords("AI Engineer working with Python, FastAPI, RAG, LLMs, Docker")
    best = pick_top(score_all(filter_repos(repos, keywords)))
    print("picked:", [r["name"] for r in best])
    print(review_repo("SutikshanUpman", best[0]))
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity


def filter_repos(repos, keywords, top_n=4):
    """Ranks repos by keyword relevance (TF-IDF) and returns the top_n."""
    if not repos or not keywords:
        return repos[:top_n]

    texts = [r["name"] + " " + r["readme"] + " " + " ".join(r["structure"]) for r in repos]
    query = " ".join(keywords)

    vectorizer = TfidfVectorizer(stop_words="english")
    matrix = vectorizer.fit_transform(texts + [query])
    scores = cosine_similarity(matrix[-1], matrix[:-1])[0]

    ranked = sorted(zip(scores, repos), key=lambda pair: pair[0], reverse=True)
    result = []
    for score, repo in ranked[:top_n]:
        repo["relevance"] = round(float(score), 3)
        result.append(repo)
    return result


if __name__ == "__main__":
    from backend.github_api.fetch import fetch_profile
    from backend.agent.keywords import get_keywords

    repos = fetch_profile("SutikshanUpman")
    keywords = get_keywords("AI Engineer working with Python, FastAPI, RAG, LLMs, Docker")
    for r in filter_repos(repos, keywords):
        print(r["relevance"], r["name"])
from fastapi import APIRouter
from pydantic import BaseModel, Field, field_validator

from backend.agent.filter import filter_repos
from backend.agent.keywords import get_keywords
from backend.agent.reviewer import pick_top, review_repo
from backend.agent.scorer import score_all
from backend.github_api.fetch import fetch_profile

router = APIRouter(tags=["reviews"])


class ReviewRequest(BaseModel):
    username: str = Field(
        min_length=1,
        max_length=39,
        pattern=r"^[a-zA-Z0-9]+(?:-[a-zA-Z0-9]+)*$",
        description="GitHub username, without a profile URL.",
    )
    job_input: str = Field(
        min_length=1,
        max_length=3000,
        description="Job description or job role to review the repositories against.",
    )

    @field_validator("username", "job_input", mode="before")
    @classmethod
    def strip_whitespace(cls, value):
        return value.strip() if isinstance(value, str) else value


class RepositoryReview(BaseModel):
    name: str
    url: str
    relevance: float
    scores: dict[str, int | float]
    total: float
    review: str


class ReviewResponse(BaseModel):
    username: str
    keywords: list[str]
    repos_fetched: int
    repos_scored: int
    reviews: list[RepositoryReview]


@router.post("/review", response_model=ReviewResponse)
def review_profile(request: ReviewRequest) -> ReviewResponse:
    """Rank and score relevant repositories, then deeply review up to two."""
    repos = fetch_profile(request.username)
    keywords = get_keywords(request.job_input)
    scored = score_all(filter_repos(repos, keywords, top_n=4))
    selected = pick_top(scored, n=2)
    reviews = [
        RepositoryReview(
            name=repo["name"],
            url=repo["url"],
            relevance=repo.get("relevance", 0),
            scores=repo["scores"],
            total=repo["total"],
            review=review_repo(request.username, repo, request.job_input),
        )
        for repo in selected
    ]
    return ReviewResponse(
        username=request.username,
        keywords=keywords,
        repos_fetched=len(repos),
        repos_scored=len(scored),
        reviews=reviews,
    )

import groq
import requests
from github import GithubException
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field, field_validator

from backend.agent.filter import filter_repos
from backend.agent.keywords import get_keywords
from backend.agent.reviewer import pick_top, review_repo
from backend.agent.scorer import score_all
from backend.github_api.fetch import fetch_profile
from backend.core.errors import ReviewError

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
    try:
        return run_review(request)
    except ReviewError as exc:
        raise HTTPException(exc.status_code, str(exc)) from exc
    except (groq.APITimeoutError, requests.Timeout) as exc:
        raise HTTPException(504, "An upstream service timed out. Please try again.") from exc
    except groq.RateLimitError as exc:
        raise HTTPException(503, "Groq rate limit reached. Please try again later.") from exc
    except groq.APIError as exc:
        raise HTTPException(502, "Groq could not complete the review. Please try again.") from exc
    except GithubException as exc:
        if exc.status == 404:
            raise HTTPException(404, "GitHub user or repository not found.") from exc
        if exc.status in (403, 429):
            raise HTTPException(503, "GitHub access is unavailable or rate limited. Please try again later.") from exc
        raise HTTPException(502, "GitHub could not complete the request.") from exc
    except requests.RequestException as exc:
        status = exc.response.status_code if exc.response is not None else None
        if status in (403, 429):
            raise HTTPException(503, "GitHub access is unavailable or rate limited. Please try again later.") from exc
        raise HTTPException(502, "GitHub could not complete the request.") from exc


def run_review(request: ReviewRequest) -> ReviewResponse:
    repos = fetch_profile(request.username)
    if not repos:
        return ReviewResponse(
            username=request.username, keywords=[], repos_fetched=0,
            repos_scored=0, reviews=[],
        )
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

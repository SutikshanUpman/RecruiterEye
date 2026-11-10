import pytest

from backend.agent.reviewer import readme_headings


# Service clients are initialized only when used.
@pytest.fixture
def scorer():
    from backend.agent import scorer

    return scorer


@pytest.fixture
def reviewer():
    from backend.agent import reviewer

    return reviewer


def test_summarize_commits_empty(scorer):
    assert scorer.summarize_commits([]) == "no commits"


def test_summarize_commits_normal(scorer):
    commits = [
        {"message": "Add search", "date": "2026-02-03T12:00:00"},
        {"message": "Create project", "date": "2026-01-01T09:00:00"},
    ]

    assert scorer.summarize_commits(commits) == (
        "2 latest commits between 2026-01-01 and 2026-02-03. "
        "Messages: Add search; Create project"
    )


def test_clean_structure_removes_junk(scorer):
    paths = [
        "app.py",
        "__pycache__/app.pyc",
        ".ipynb_checkpoints/demo.ipynb",
        "node_modules/package/index.js",
        ".DS_Store",
        "src/service.py",
    ]

    assert scorer.clean_structure(paths) == ["app.py", "src/service.py"]


def test_clean_structure_keeps_gitignore(scorer):
    assert scorer.clean_structure([".gitignore", "app.py"]) == [
        ".gitignore",
        "app.py",
    ]


def test_clean_structure_caps_at_50(scorer):
    paths = [f"src/file_{i}.py" for i in range(52)]

    assert scorer.clean_structure(paths) == paths[:50]


def test_pick_code_files_skips_tests_and_init(reviewer):
    paths = ["tests/test_app.py", "src/__init__.py", "src/app.py"]

    assert reviewer.pick_code_files(paths) == ["src/app.py"]


def test_pick_code_files_shallow_first_and_limited(reviewer):
    paths = ["src/deep/worker.py", "src/app.py", "main.py", "other.js"]

    assert reviewer.pick_code_files(paths) == ["main.py", "other.js", "src/app.py"]


def test_pick_code_files_source_extensions_only(reviewer):
    paths = [
        "main.py", "app.js", "types.ts", "Main.java", "main.cpp", "main.go",
        "README.md", "styles.css", "data.json", "image.png",
    ]

    assert reviewer.pick_code_files(paths, n=10) == paths[:6]


def test_pick_top_uses_quality_and_relevance(reviewer):
    repos = [
        {"name": "quality", "total": 30, "relevance": 0.1},
        {"name": "balanced", "total": 24, "relevance": 1.0},
        {"name": "weak", "total": 0, "relevance": 0.5},
    ]

    assert reviewer.pick_top(repos) == [repos[1], repos[0]]
    assert reviewer.pick_top(repos, n=1) == [repos[1]]


def test_filter_repos_ranks_best_match_and_adds_relevance():
    from backend.agent.filter import filter_repos

    repos = [
        {
            "name": "garden", "url": "", "readme": "flowers plants soil",
            "structure": ["garden.txt"], "commits": [],
        },
        {
            "name": "python-api", "url": "", "readme": "python fastapi",
            "structure": ["main.py"], "commits": [],
        },
        {
            "name": "recipes", "url": "", "readme": "bread flour cooking",
            "structure": ["recipes.txt"], "commits": [],
        },
    ]

    ranked = filter_repos(repos, ["python", "fastapi"], top_n=3)

    assert len(ranked) == 3
    assert ranked[0] is repos[1]
    assert all("relevance" in repo for repo in ranked)
    assert ranked[0]["relevance"] > ranked[1]["relevance"]


def test_readme_headings():
    text = "# Title\nsome text\n## Setup\nmore text"
    assert readme_headings(text) == ["# Title", "## Setup"]

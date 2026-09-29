"""Источник событий из Git (заготовка). Требует extra `git`: pip install -e ".[git]"."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass
class CommitInfo:
    sha: str
    message: str
    files_changed: int
    insertions: int
    deletions: int


def read_commits(repo_path: str, since: str | None = None) -> list[CommitInfo]:
    """Читает историю коммитов. LOC здесь — контекст, НЕ прогресс (ADR-0002)."""
    from git import Repo  # lazy import

    repo = Repo(repo_path)
    kwargs = {"since": since} if since else {}
    out = []
    for c in repo.iter_commits(**kwargs):
        s = c.stats.total
        out.append(CommitInfo(c.hexsha, c.message.strip(), s["files"], s["insertions"], s["deletions"]))
    return out


# TODO: сопоставление commit/PR → requirement_id (по issue-ссылкам, путям файлов, тегам в сообщении)
# TODO: адаптеры CI (GitHub Actions / GitLab CI) → Evidence(kind=CI, q_observed=passed/required)

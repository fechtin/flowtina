"""Content source endpoints: topics, RSS feeds, keywords."""

from __future__ import annotations

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_current_user, get_owned_project
from app.core.database import get_db
from app.models.project import Project
from app.models.user import User
from app.repositories.repositories import (
    KeywordSourceRepository,
    RSSSourceRepository,
    TopicRepository,
)
from app.schemas.common import ok
from app.schemas.content import (
    KeywordCreate,
    KeywordOut,
    RSSCreate,
    RSSOut,
    TopicCreate,
    TopicOut,
)
from app.services.source_service import SourceService

router = APIRouter(tags=["sources"])


@router.get("/projects/{project_id}/topics")
def list_topics(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = TopicRepository(db).list(project_id=project.id)
    return ok([TopicOut.model_validate(t).model_dump() for t in items])


@router.post("/projects/{project_id}/topics")
def create_topic(
    payload: TopicCreate, project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
):
    topic = TopicRepository(db).create(project_id=project.id, **payload.model_dump())
    db.commit()
    db.refresh(topic)
    return ok(TopicOut.model_validate(topic).model_dump(), "Topic created")


@router.delete("/topics/{topic_id}")
def delete_topic(topic_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = TopicRepository(db)
    topic = repo.get(topic_id)
    if topic:
        repo.soft_delete(topic)
        db.commit()
    return ok(message="Topic deleted")


@router.get("/projects/{project_id}/rss")
def list_rss(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = RSSSourceRepository(db).list(project_id=project.id)
    return ok([RSSOut.model_validate(r).model_dump() for r in items])


@router.post("/projects/{project_id}/rss")
def create_rss(
    payload: RSSCreate, project: Project = Depends(get_owned_project), db: Session = Depends(get_db)
):
    rss = RSSSourceRepository(db).create(project_id=project.id, url=payload.url)
    db.commit()
    db.refresh(rss)
    return ok(RSSOut.model_validate(rss).model_dump(), "RSS source added")


@router.delete("/rss/{rss_id}")
def delete_rss(rss_id: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    repo = RSSSourceRepository(db)
    rss = repo.get(rss_id)
    if rss:
        repo.soft_delete(rss)
        db.commit()
    return ok(message="RSS source deleted")


@router.get("/projects/{project_id}/keywords")
def list_keywords(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    items = KeywordSourceRepository(db).list(project_id=project.id)
    return ok([KeywordOut.model_validate(k).model_dump() for k in items])


@router.post("/projects/{project_id}/keywords")
def create_keyword(
    payload: KeywordCreate,
    project: Project = Depends(get_owned_project),
    db: Session = Depends(get_db),
):
    kw = KeywordSourceRepository(db).create(project_id=project.id, **payload.model_dump())
    db.commit()
    db.refresh(kw)
    return ok(KeywordOut.model_validate(kw).model_dump(), "Keyword added")


@router.post("/projects/{project_id}/sources/sync")
async def sync_sources(project: Project = Depends(get_owned_project), db: Session = Depends(get_db)):
    docs = await SourceService(db).collect(project.id)
    return ok({"collected": len(docs)}, "Sources synced")

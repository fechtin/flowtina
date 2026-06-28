"""Unit tests for manual deletion of Growth trends and drafts (soft delete)."""

from app.growth.models import ContentDraft, TrendTopic
from app.growth.service import GrowthService

PAGE = "page-del-1"
OTHER = "page-del-2"


def _topic(page_id: str, title: str) -> TrendTopic:
    return TrendTopic(page_id=page_id, title=title, status="new")


def _draft(page_id: str, body: str) -> ContentDraft:
    return ContentDraft(page_id=page_id, content_type="post", body=body, status="pending_review")


def test_delete_draft_hides_it_from_list(db_session):
    svc = GrowthService(db_session)
    keep, drop = _draft(PAGE, "keep"), _draft(PAGE, "drop")
    db_session.add_all([keep, drop])
    db_session.commit()

    svc.delete_draft(drop.id, PAGE)

    listed = svc.list_drafts(PAGE)
    assert [d.id for d in listed] == [keep.id]
    assert svc.get_draft(drop.id, PAGE) is None
    assert drop.deleted_at is not None  # soft delete, row still present


def test_delete_all_drafts_scoped_to_page(db_session):
    svc = GrowthService(db_session)
    db_session.add_all([_draft(PAGE, "a"), _draft(PAGE, "b"), _draft(OTHER, "c")])
    db_session.commit()

    removed = svc.delete_all_drafts(PAGE)

    assert removed == 2
    assert svc.list_drafts(PAGE) == []
    assert len(svc.list_drafts(OTHER)) == 1  # other page untouched


def test_delete_topic_hides_it_from_list(db_session):
    svc = GrowthService(db_session)
    keep, drop = _topic(PAGE, "keep"), _topic(PAGE, "drop")
    db_session.add_all([keep, drop])
    db_session.commit()

    svc.delete_topic(drop.id, PAGE)

    assert [t.id for t in svc.list_topics(PAGE)] == [keep.id]
    assert drop.deleted_at is not None


def test_delete_all_topics_scoped_to_page(db_session):
    svc = GrowthService(db_session)
    db_session.add_all([_topic(PAGE, "a"), _topic(PAGE, "b"), _topic(OTHER, "c")])
    db_session.commit()

    removed = svc.delete_all_topics(PAGE)

    assert removed == 2
    assert svc.list_topics(PAGE) == []
    assert len(svc.list_topics(OTHER)) == 1


def test_delete_missing_draft_raises(db_session):
    svc = GrowthService(db_session)
    try:
        svc.delete_draft("nope", PAGE)
        raise AssertionError("expected ValueError")
    except ValueError:
        pass

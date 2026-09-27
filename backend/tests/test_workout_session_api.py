from datetime import UTC, datetime, timedelta
from uuid import UUID, uuid4

import pytest
import pytest_asyncio
from app.db.models import (
    Exercise,
    MuscleGroup,
    WorkoutSession,
    WorkoutSessionExercise,
    WorkoutSessionSet,
    WorkoutTemplate,
)
from app.services import auth as auth_service
from app.services import workout_session as workout_session_service
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


@pytest.mark.asyncio
async def test_stats_api_averages_only_owned_completed_sessions(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, owner = await login(api_client, "stats_owner")
    other_headers, other = await login(api_client, "stats_other")
    start = datetime(2026, 9, 27, tzinfo=UTC)
    db_session.add_all(
        [
            WorkoutSession(
                user_id=owner,
                name="Completed",
                status="completed",
                started_at=start,
                completed_at=start + timedelta(seconds=seconds),
            )
            for seconds in [60, 61]
        ]
    )
    db_session.add_all(
        [
            WorkoutSession(
                user_id=owner, name="Active", status="in_progress", started_at=start
            ),
            WorkoutSession(
                user_id=owner, name="Cancelled", status="cancelled", started_at=start
            ),
            WorkoutSession(
                user_id=other,
                name="Private",
                status="completed",
                started_at=start,
                completed_at=start + timedelta(seconds=9000),
            ),
        ]
    )
    await db_session.commit()
    for auth, count, average in [(headers, 2, 60.5), (other_headers, 1, 9000.0)]:
        response = await api_client.get("/workout-sessions/stats", headers=auth)
        assert response.status_code == 200, response.text
        assert response.json() == {
            "completed_sessions_count": count,
            "average_duration_seconds": average,
        }


@pytest.mark.asyncio
async def test_stats_api_returns_zero_and_null_without_completed_sessions(
    api_client: AsyncClient, editable_set
) -> None:
    headers, _, _ = editable_set
    response = await api_client.get("/workout-sessions/stats", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {
        "completed_sessions_count": 0,
        "average_duration_seconds": None,
    }


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
@pytest.mark.asyncio
async def test_stats_api_requires_authentication(
    api_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await api_client.get("/workout-sessions/stats", headers=headers)
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_history_api_paginates_and_hides_private_and_active_sessions(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, owner = await login(api_client, "history_owner")
    _, other = await login(api_client, "history_other")
    start = datetime(2026, 9, 27, tzinfo=UTC)
    for number, status in [(1, "completed"), (2, "cancelled"), (3, "in_progress")]:
        db_session.add(
            WorkoutSession(
                id=UUID(int=number),
                user_id=owner,
                name=str(number),
                status=status,
                started_at=start,
                completed_at=start + timedelta(minutes=30)
                if status == "completed"
                else None,
                exercises=[
                    WorkoutSessionExercise(
                        position=0,
                        exercise_snapshot={
                            "names": {"en": "Squat"},
                            "muscle_groups": [],
                        },
                        sets=[
                            WorkoutSessionSet(
                                position=0, set_type="working", planned_reps=8
                            )
                        ],
                    )
                ],
            )
        )
    db_session.add(
        WorkoutSession(
            user_id=other,
            name="Private",
            status="cancelled",
            started_at=start + timedelta(days=1),
        )
    )
    await db_session.commit()
    for offset, expected in [(0, 2), (1, 1), (2, None)]:
        response = await api_client.get(
            f"/workout-sessions?limit=1&offset={offset}", headers=headers
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert (body["total"], body["limit"], body["offset"]) == (2, 1, offset)
        if expected is None:
            assert body["items"] == []
        else:
            assert len(body["items"]) == 1
            item = body["items"][0]
            assert item["id"] == str(UUID(int=expected))
            assert item["duration_seconds"] == (1800 if expected == 1 else None)
            assert item["exercises"][0]["sets"][0]["planned_reps"] == 8


@pytest.mark.asyncio
async def test_history_api_empty_page_defaults(api_client: AsyncClient) -> None:
    headers, _ = await login(api_client, "empty_history")
    response = await api_client.get("/workout-sessions", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json() == {"items": [], "total": 0, "limit": 20, "offset": 0}


@pytest.mark.parametrize(
    "query", ["limit=0", "limit=101", "limit=abc", "offset=-1", "offset=1.5"]
)
@pytest.mark.asyncio
async def test_history_api_validates_pagination(
    api_client: AsyncClient, query: str
) -> None:
    headers, _ = await login(api_client, "history_validation")
    response = await api_client.get(f"/workout-sessions?{query}", headers=headers)
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
@pytest.mark.asyncio
async def test_history_api_requires_auth(
    api_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await api_client.get("/workout-sessions", headers=headers)
    assert response.status_code == 401, response.text


@pytest.mark.asyncio
async def test_cancel_api_preserves_results_and_is_repeatable(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    url = f"/workout-sessions/{workout_id}"
    recorded = await api_client.patch(
        f"{url}/sets/{set_id}",
        headers=headers,
        json={"actual_reps": 8, "status": "completed"},
    )
    assert recorded.status_code == 200
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.post(f"{url}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    expected = {**original, "status": "cancelled"}
    assert response.json() == expected
    assert (await api_client.get(url, headers=headers)).json() == expected
    repeated = await api_client.post(f"{url}/cancel", headers=headers)
    assert repeated.status_code == 200 and repeated.json() == expected
    active = await api_client.get("/workout-sessions/active", headers=headers)
    assert active.status_code == 200 and active.json() is None
    edit = await api_client.patch(
        f"{url}/sets/{set_id}", headers=headers, json={"actual_reps": 10}
    )
    assert edit.status_code == 409
    complete = await api_client.post(f"{url}/complete", headers=headers)
    assert complete.status_code == 409
    assert (await api_client.get(url, headers=headers)).json() == expected


@pytest.mark.asyncio
async def test_cancel_api_allows_empty_session(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    exercise_id = original["exercises"][0]["id"]
    deleted = await api_client.delete(f"{url}/exercises/{exercise_id}", headers=headers)
    assert deleted.status_code == 200
    response = await api_client.post(f"{url}/cancel", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["status"] == "cancelled"
    assert response.json()["exercises"] == []


@pytest.mark.asyncio
async def test_cancel_api_rejects_completed_session(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = "completed"
    workout.completed_at = workout.started_at
    await db_session.commit()
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.post(f"{url}/cancel", headers=headers)
    assert response.status_code == 409, response.text
    assert (await api_client.get(url, headers=headers)).json() == original


@pytest.mark.parametrize("case", ["no_auth", "other_user", "missing"])
@pytest.mark.asyncio
async def test_cancel_api_enforces_ownership(
    api_client: AsyncClient, editable_set, case: str
) -> None:
    headers, workout_id, _ = editable_set
    other_headers, _ = await login(api_client, "cancel_outsider")
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    target = uuid4() if case == "missing" else workout_id
    response = await api_client.post(f"/workout-sessions/{target}/cancel", headers=auth)
    assert response.status_code == (401 if case == "no_auth" else 404), response.text
    saved = (
        await api_client.get(f"/workout-sessions/{workout_id}", headers=headers)
    ).json()
    assert saved["status"] == "in_progress"


@pytest.mark.asyncio
async def test_complete_api_records_duration_and_locks_workout(
    api_client: AsyncClient, editable_set, monkeypatch: pytest.MonkeyPatch
) -> None:
    # SQLite drops timezone offsets. Match its storage for this HTTP workflow test;
    # UTC timestamp behavior requires a separate PostgreSQL integration test.
    class SQLiteClock:
        @staticmethod
        def now(tz):
            return datetime.now(tz).replace(tzinfo=None)

    monkeypatch.setattr(workout_session_service, "datetime", SQLiteClock)
    headers, workout_id, set_id = editable_set
    url = f"/workout-sessions/{workout_id}"
    recorded = await api_client.patch(
        f"{url}/sets/{set_id}",
        headers=headers,
        json={"actual_reps": 8, "actual_weight_kg": "20.00", "status": "completed"},
    )
    assert recorded.status_code == 200, recorded.text
    exercise_id = recorded.json()["exercises"][0]["id"]
    added = await api_client.post(
        f"{url}/exercises/{exercise_id}/sets", headers=headers, json={}
    )
    assert added.status_code == 201, added.text
    response = await api_client.post(f"{url}/complete", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["status"] == "completed"
    assert body["completed_at"] is not None
    assert isinstance(body["duration_seconds"], int) and body["duration_seconds"] >= 0
    assert [s["status"] for s in body["exercises"][0]["sets"]] == [
        "completed",
        "skipped",
    ]
    assert body["exercises"][0]["sets"][0] == recorded.json()["exercises"][0]["sets"][0]
    saved = (await api_client.get(url, headers=headers)).json()
    repeated = await api_client.post(f"{url}/complete", headers=headers)
    assert repeated.status_code == 200
    assert repeated.json() == saved
    # SQLite strips timezone offsets on reload; compare instants explicitly.
    assert datetime.fromisoformat(saved["completed_at"]).replace(
        tzinfo=UTC
    ) == datetime.fromisoformat(body["completed_at"]).replace(tzinfo=UTC)
    active = await api_client.get("/workout-sessions/active", headers=headers)
    assert active.status_code == 200 and active.json() is None
    edit = await api_client.patch(
        f"{url}/sets/{set_id}", headers=headers, json={"actual_reps": 10}
    )
    assert edit.status_code == 409
    assert (await api_client.get(url, headers=headers)).json() == saved


@pytest.mark.parametrize("case", ["pending", "empty", "cancelled"])
@pytest.mark.asyncio
async def test_complete_api_rejects_invalid_state(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, _ = editable_set
    url = f"/workout-sessions/{workout_id}"
    if case == "empty":
        detail = (await api_client.get(url, headers=headers)).json()
        exercise_id = detail["exercises"][0]["id"]
        deleted = await api_client.delete(
            f"{url}/exercises/{exercise_id}", headers=headers
        )
        assert deleted.status_code == 200
    elif case == "cancelled":
        workout = await db_session.get(WorkoutSession, workout_id)
        workout.status = "cancelled"
        await db_session.commit()
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.post(f"{url}/complete", headers=headers)
    assert response.status_code == 409, response.text
    assert (await api_client.get(url, headers=headers)).json() == original


@pytest.mark.parametrize("case", ["no_auth", "other_user", "missing"])
@pytest.mark.asyncio
async def test_complete_api_enforces_ownership(
    api_client: AsyncClient, editable_set, case: str
) -> None:
    headers, workout_id, _ = editable_set
    other_headers, _ = await login(api_client, "complete_outsider")
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    target = uuid4() if case == "missing" else workout_id
    response = await api_client.post(
        f"/workout-sessions/{target}/complete", headers=auth
    )
    assert response.status_code == (401 if case == "no_auth" else 404), response.text
    saved = (
        await api_client.get(f"/workout-sessions/{workout_id}", headers=headers)
    ).json()
    assert saved["status"] == "in_progress" and saved["completed_at"] is None


@pytest.mark.asyncio
async def test_reorder_api_persists_requested_order(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    db_session.add(
        WorkoutSessionExercise(
            session_id=workout_id,
            position=3,
            notes="Keep",
            exercise_snapshot={"names": {"en": "Row"}, "muscle_groups": []},
            sets=[WorkoutSessionSet(position=0, set_type="working", planned_reps=8)],
        )
    )
    await db_session.commit()
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    desired = [e["id"] for e in reversed(original["exercises"])]
    response = await api_client.post(
        f"{url}/exercises/reorder", headers=headers, json={"exercise_ids": desired}
    )
    assert response.status_code == 200, response.text
    expected = [
        {**e, "position": i} for i, e in enumerate(reversed(original["exercises"]))
    ]
    assert response.json()["exercises"] == expected
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"] == expected


@pytest.mark.parametrize(
    "case", ["empty", "duplicate", "invalid_uuid", "extra_field", "missing_field"]
)
@pytest.mark.asyncio
async def test_reorder_api_validates_payload(
    api_client: AsyncClient, editable_set, case: str
) -> None:
    headers, workout_id, _ = editable_set
    uid = str(uuid4())
    payload = {"exercise_ids": [uid]}
    if case == "empty":
        payload = {"exercise_ids": []}
    elif case == "duplicate":
        payload = {"exercise_ids": [uid, uid]}
    elif case == "invalid_uuid":
        payload = {"exercise_ids": ["bad"]}
    elif case == "extra_field":
        payload = {"exercise_ids": [uid], "position": 0}
    else:
        payload = {}
    response = await api_client.post(
        f"/workout-sessions/{workout_id}/exercises/reorder",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "case",
    [
        "no_auth",
        "other_user",
        "missing_session",
        "unknown_exercise",
        "foreign_exercise",
        "omitted",
        "completed",
        "cancelled",
    ],
)
@pytest.mark.asyncio
async def test_reorder_api_rejects_invalid_operation(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, _ = editable_set
    other_headers, other_id = await login(api_client, "reorder_outsider")
    foreign = WorkoutSessionExercise(
        position=0, exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []}
    )
    db_session.add(WorkoutSession(user_id=other_id, name="Other", exercises=[foreign]))
    if case == "omitted":
        db_session.add(
            WorkoutSessionExercise(
                session_id=workout_id,
                position=1,
                exercise_snapshot={"names": {"en": "Extra"}, "muscle_groups": []},
            )
        )
    if case in {"completed", "cancelled"}:
        workout = await db_session.get(WorkoutSession, workout_id)
        workout.status = case
        workout.completed_at = workout.started_at if case == "completed" else None
    await db_session.commit()
    foreign_id = str(foreign.id)
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    ids = [original["exercises"][0]["id"]]
    if case == "unknown_exercise":
        ids = [str(uuid4())]
    elif case == "foreign_exercise":
        ids = [foreign_id]
    target = uuid4() if case == "missing_session" else workout_id
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    response = await api_client.post(
        f"/workout-sessions/{target}/exercises/reorder",
        headers=auth,
        json={"exercise_ids": ids},
    )
    expected = (
        401
        if case == "no_auth"
        else 404
        if case in {"other_user", "missing_session"}
        else 409
    )
    assert response.status_code == expected, response.text
    saved = await api_client.get(url, headers=headers)
    assert saved.json() == original


@pytest.mark.asyncio
async def test_replace_exercise_api_persists_fresh_sets(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, old_set_id = editable_set
    replacement = Exercise(code="replacement", names={"en": "Row"})
    db_session.add(replacement)
    await db_session.commit()
    replacement_id = str(replacement.id)
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()["exercises"][0]
    response = await api_client.post(
        f"{url}/exercises/{original['id']}/replace",
        headers=headers,
        json={
            "exercise_id": replacement_id,
            "notes": "New",
            "sets": [{"set_type": "warmup"}, {}],
        },
    )
    assert response.status_code == 200, response.text
    item = response.json()["exercises"][0]
    assert item["id"] == original["id"] and item["position"] == original["position"]
    assert item["exercise_id"] == replacement_id and item["notes"] == "New"
    assert item["exercise_snapshot"]["names"] == {"en": "Row"}
    assert [s["set_type"] for s in item["sets"]] == ["warmup", "working"]
    assert all(
        s["id"] != str(old_set_id)
        and s["status"] == "pending"
        and s["planned_reps"] is None
        for s in item["sets"]
    )
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"][0] == item
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionSet, old_set_id) is None


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"exercise_id": "bad", "sets": [{}]},
        {"exercise_id": str(uuid4()), "sets": []},
        {"exercise_id": str(uuid4()), "sets": [{}], "position": 1},
    ],
)
@pytest.mark.asyncio
async def test_replace_exercise_api_validates_body(
    api_client: AsyncClient, editable_set, payload
) -> None:
    headers, workout_id, _ = editable_set
    response = await api_client.post(
        f"/workout-sessions/{workout_id}/exercises/{uuid4()}/replace",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "case", ["completed_set", "completed_session", "cancelled_session"]
)
@pytest.mark.asyncio
async def test_replace_exercise_api_rejects_protected_state(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    item = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = item.session_exercise_id
    if case == "completed_set":
        item.status = "completed"
        item.actual_reps = 8
        item.completed_at = datetime.now(UTC)
    else:
        workout = await db_session.get(WorkoutSession, workout_id)
        workout.status = case.removesuffix("_session")
        workout.completed_at = (
            workout.started_at if case == "completed_session" else None
        )
    await db_session.commit()
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.post(
        f"{url}/exercises/{exercise_id}/replace",
        headers=headers,
        json={"exercise_id": str(uuid4()), "sets": [{}]},
    )
    assert response.status_code == 409, response.text
    saved = await api_client.get(url, headers=headers)
    assert saved.json() == original


@pytest.mark.parametrize(
    "case",
    [
        "no_auth",
        "other_user",
        "missing_session",
        "missing_exercise",
        "foreign_exercise",
        "missing_catalog",
        "private_catalog",
    ],
)
@pytest.mark.asyncio
async def test_replace_exercise_api_rejects_wrong_resource(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    other_headers, other_id = await login(api_client, "replace_outsider")
    item = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = item.session_exercise_id
    foreign = WorkoutSessionExercise(
        position=0, exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []}
    )
    private = Exercise(owner_user_id=other_id, names={"en": "Private"})
    public = Exercise(code="public-replacement", names={"en": "Public"})
    db_session.add_all(
        [
            private,
            public,
            WorkoutSession(user_id=other_id, name="Other", exercises=[foreign]),
        ]
    )
    await db_session.commit()
    target_session = uuid4() if case == "missing_session" else workout_id
    target_exercise = (
        foreign.id
        if case == "foreign_exercise"
        else uuid4()
        if case == "missing_exercise"
        else exercise_id
    )
    catalog_id = (
        private.id
        if case == "private_catalog"
        else uuid4()
        if case == "missing_catalog"
        else public.id
    )
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.post(
        f"/workout-sessions/{target_session}/exercises/{target_exercise}/replace",
        headers=auth,
        json={"exercise_id": str(catalog_id), "sets": [{}]},
    )
    assert response.status_code == (401 if case == "no_auth" else 404), response.text
    saved = await api_client.get(url, headers=headers)
    assert saved.json() == original


@pytest.mark.asyncio
async def test_delete_exercise_api_persists_and_removes_sets(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    exercise_id = original["exercises"][0]["id"]
    response = await api_client.delete(
        f"{url}/exercises/{exercise_id}", headers=headers
    )
    assert response.status_code == 200, response.text
    assert response.json()["exercises"] == []
    assert response.json()["status"] == "in_progress"
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"] == []
    db_session.expunge_all()
    assert await db_session.get(WorkoutSessionSet, set_id) is None
    repeated = await api_client.delete(
        f"{url}/exercises/{exercise_id}", headers=headers
    )
    assert repeated.status_code == 404


@pytest.mark.parametrize(
    "case", ["completed_set", "completed_session", "cancelled_session"]
)
@pytest.mark.asyncio
async def test_delete_exercise_api_rejects_protected_state(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    item = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = item.session_exercise_id
    if case == "completed_set":
        item.status = "completed"
        item.actual_reps = 8
        item.completed_at = datetime.now(UTC)
    else:
        workout = await db_session.get(WorkoutSession, workout_id)
        workout.status = case.removesuffix("_session")
        workout.completed_at = (
            workout.started_at if case == "completed_session" else None
        )
    await db_session.commit()
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.delete(
        f"{url}/exercises/{exercise_id}", headers=headers
    )
    assert response.status_code == 409, response.text
    saved = await api_client.get(url, headers=headers)
    assert saved.json() == original


@pytest.mark.parametrize(
    "case",
    ["no_auth", "other_user", "missing_session", "missing_exercise", "other_exercise"],
)
@pytest.mark.asyncio
async def test_delete_exercise_api_rejects_wrong_resource(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    other_headers, other_id = await login(api_client, "exercise_deleter")
    item = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = item.session_exercise_id
    foreign = WorkoutSessionExercise(
        position=0, exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []}
    )
    db_session.add(WorkoutSession(user_id=other_id, name="Other", exercises=[foreign]))
    await db_session.commit()
    foreign_id = foreign.id
    target_session = uuid4() if case == "missing_session" else workout_id
    target_exercise = (
        foreign_id
        if case == "other_exercise"
        else uuid4()
        if case == "missing_exercise"
        else exercise_id
    )
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    response = await api_client.delete(
        f"/workout-sessions/{target_session}/exercises/{target_exercise}", headers=auth
    )
    assert response.status_code == (401 if case == "no_auth" else 404), response.text
    assert await db_session.get(WorkoutSessionExercise, exercise_id) is not None
    assert await db_session.get(WorkoutSessionExercise, foreign_id) is not None


@pytest.mark.asyncio
async def test_delete_set_api_persists_and_returns_updated_session(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    exercise_id = original["exercises"][0]["id"]
    added = await api_client.post(
        f"{url}/exercises/{exercise_id}/sets", headers=headers, json={}
    )
    assert added.status_code == 201, added.text
    remaining = added.json()["exercises"][0]["sets"][1]
    response = await api_client.delete(f"{url}/sets/{set_id}", headers=headers)
    assert response.status_code == 200, response.text
    assert response.json()["exercises"][0]["sets"] == [remaining]
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"] == response.json()["exercises"]
    repeated = await api_client.delete(f"{url}/sets/{set_id}", headers=headers)
    assert repeated.status_code == 404


@pytest.mark.parametrize(
    "case", ["last_set", "completed_set", "completed_session", "cancelled_session"]
)
@pytest.mark.asyncio
async def test_delete_set_api_rejects_business_rule_violation(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    item = await db_session.get(WorkoutSessionSet, set_id)
    if case == "completed_set":
        db_session.add(
            WorkoutSessionSet(
                session_exercise_id=item.session_exercise_id,
                position=1,
                set_type="working",
            )
        )
        item.status = "completed"
        item.actual_reps = 8
        item.completed_at = datetime.now(UTC)
    if case in {"completed_session", "cancelled_session"}:
        workout = await db_session.get(WorkoutSession, workout_id)
        workout.status = case.removesuffix("_session")
        workout.completed_at = (
            workout.started_at if case == "completed_session" else None
        )
    await db_session.commit()
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.delete(f"{url}/sets/{set_id}", headers=headers)
    assert response.status_code == 409, response.text
    saved = await api_client.get(url, headers=headers)
    assert saved.json() == original


@pytest.mark.parametrize(
    "case", ["no_auth", "other_user", "missing_session", "missing_set", "other_set"]
)
@pytest.mark.asyncio
async def test_delete_set_api_rejects_wrong_resource(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    other_headers, other_id = await login(api_client, "delete_outsider")
    foreign_set = WorkoutSessionSet(position=0, set_type="working")
    db_session.add(
        WorkoutSession(
            user_id=other_id,
            name="Other",
            exercises=[
                WorkoutSessionExercise(
                    position=0,
                    exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []},
                    sets=[foreign_set],
                )
            ],
        )
    )
    await db_session.commit()
    foreign_id = foreign_set.id
    target_session = uuid4() if case == "missing_session" else workout_id
    target_set = (
        foreign_id
        if case == "other_set"
        else uuid4()
        if case == "missing_set"
        else set_id
    )
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    response = await api_client.delete(
        f"/workout-sessions/{target_session}/sets/{target_set}", headers=auth
    )
    assert response.status_code == (401 if case == "no_auth" else 404), response.text
    assert await db_session.get(WorkoutSessionSet, set_id) is not None
    assert await db_session.get(WorkoutSessionSet, foreign_id) is not None


@pytest.mark.parametrize(
    "payload,expected_type", [({}, "working"), ({"set_type": "warmup"}, "warmup")]
)
@pytest.mark.asyncio
async def test_add_set_api_persists_new_set(
    api_client: AsyncClient, editable_set, payload, expected_type: str
) -> None:
    headers, workout_id, _ = editable_set
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    exercise_id = original["exercises"][0]["id"]
    response = await api_client.post(
        f"{url}/exercises/{exercise_id}/sets", headers=headers, json=payload
    )
    assert response.status_code == 201, response.text
    sets = response.json()["exercises"][0]["sets"]
    assert len(sets) == 2
    assert sets[0] == original["exercises"][0]["sets"][0]
    assert sets[1]["position"] == 1
    assert sets[1]["set_type"] == expected_type
    assert sets[1]["status"] == "pending"
    assert sets[1]["actual_reps"] is None
    assert sets[1]["actual_weight_kg"] is None
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"][0]["sets"] == sets


@pytest.mark.parametrize(
    "payload",
    [
        {"set_type": "invalid"},
        {"set_type": None},
        {"position": 4},
        {"status": "completed"},
    ],
)
@pytest.mark.asyncio
async def test_add_set_api_validates_body(
    api_client: AsyncClient, editable_set, payload
) -> None:
    headers, workout_id, _ = editable_set
    response = await api_client.post(
        f"/workout-sessions/{workout_id}/exercises/{uuid4()}/sets",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize(
    "case",
    ["no_auth", "other_user", "missing_session", "missing_exercise", "other_exercise"],
)
@pytest.mark.asyncio
async def test_add_set_api_rejects_wrong_resource(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, case: str
) -> None:
    headers, workout_id, set_id = editable_set
    other_headers, other_id = await login(api_client, "set_outsider")
    original_set = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = original_set.session_exercise_id
    foreign = WorkoutSessionExercise(
        position=0, exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []}
    )
    db_session.add(WorkoutSession(user_id=other_id, name="Other", exercises=[foreign]))
    await db_session.commit()
    target_session = uuid4() if case == "missing_session" else workout_id
    target_exercise = (
        foreign.id
        if case == "other_exercise"
        else uuid4()
        if case == "missing_exercise"
        else exercise_id
    )
    auth = (
        {} if case == "no_auth" else other_headers if case == "other_user" else headers
    )
    response = await api_client.post(
        f"/workout-sessions/{target_session}/exercises/{target_exercise}/sets",
        headers=auth,
        json={},
    )
    assert response.status_code == (401 if case == "no_auth" else 404), response.text
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 1
    )


@pytest.mark.parametrize("closed_status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_add_set_api_rejects_closed_session(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, closed_status: str
) -> None:
    headers, workout_id, set_id = editable_set
    original_set = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = original_set.session_exercise_id
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = closed_status
    workout.completed_at = workout.started_at if closed_status == "completed" else None
    await db_session.commit()
    response = await api_client.post(
        f"/workout-sessions/{workout_id}/exercises/{exercise_id}/sets",
        headers=headers,
        json={},
    )
    assert response.status_code == 409, response.text
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSessionSet))
        == 1
    )


@pytest.mark.asyncio
async def test_add_exercise_api_persists_ordered_sets(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    exercise = Exercise(code="test-bench", names={"en": "Bench"})
    db_session.add(exercise)
    await db_session.commit()
    exercise_id = str(exercise.id)
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    response = await api_client.post(
        f"{url}/exercises",
        headers=headers,
        json={
            "exercise_id": exercise_id,
            "notes": "Extra",
            "sets": [{"set_type": "warmup"}, {}],
        },
    )
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["exercises"][0] == original["exercises"][0]
    added = body["exercises"][1]
    assert added["exercise_id"] == exercise_id
    assert added["position"] == 1
    assert added["notes"] == "Extra"
    assert added["exercise_snapshot"]["names"] == {"en": "Bench"}
    assert [item["position"] for item in added["sets"]] == [0, 1]
    assert [item["set_type"] for item in added["sets"]] == ["warmup", "working"]
    assert all(item["status"] == "pending" for item in added["sets"])
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"] == body["exercises"]


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"exercise_id": "invalid", "sets": [{}]},
        {"exercise_id": str(uuid4()), "sets": []},
        {"exercise_id": str(uuid4()), "sets": [{}], "user_id": str(uuid4())},
    ],
)
@pytest.mark.asyncio
async def test_add_exercise_api_validates_input(
    api_client: AsyncClient, editable_set, payload: dict[str, object]
) -> None:
    headers, workout_id, _ = editable_set
    response = await api_client.post(
        f"/workout-sessions/{workout_id}/exercises", headers=headers, json=payload
    )
    assert response.status_code == 422, response.text


@pytest.mark.parametrize("closed_status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_add_exercise_api_rejects_closed_session(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, closed_status: str
) -> None:
    headers, workout_id, _ = editable_set
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = closed_status
    workout.completed_at = workout.started_at if closed_status == "completed" else None
    await db_session.commit()
    response = await api_client.post(
        f"/workout-sessions/{workout_id}/exercises",
        headers=headers,
        json={"exercise_id": str(uuid4()), "sets": [{}]},
    )
    assert response.status_code == 409, response.text


@pytest.mark.asyncio
async def test_add_exercise_api_auth_and_private_resources(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    other_headers, other_id = await login(api_client, "other_adder")
    private = Exercise(owner_user_id=other_id, names={"en": "Private"})
    db_session.add(private)
    await db_session.commit()
    private_id = str(private.id)
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    cases = [
        ({}, workout_id, private_id, 401),
        (other_headers, workout_id, private_id, 404),
        (headers, uuid4(), private_id, 404),
        (headers, workout_id, private_id, 404),
        (headers, workout_id, str(uuid4()), 404),
    ]
    for auth, session_id, exercise_id, expected in cases:
        response = await api_client.post(
            f"/workout-sessions/{session_id}/exercises",
            headers=auth,
            json={"exercise_id": exercise_id, "sets": [{}]},
        )
        assert response.status_code == expected, response.text
    saved = await api_client.get(url, headers=headers)
    assert saved.json()["exercises"] == original["exercises"]


@pytest.mark.asyncio
async def test_patch_exercise_notes_persist_and_clear(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    detail_url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(detail_url, headers=headers)).json()
    exercise_id = original["exercises"][0]["id"]
    for notes in ["Повільний рух", None]:
        response = await api_client.patch(
            f"{detail_url}/exercises/{exercise_id}",
            headers=headers,
            json={"notes": notes},
        )
        assert response.status_code == 200, response.text
        body = response.json()
        assert body["exercises"][0]["notes"] == notes
        assert body["notes"] == original["notes"]
        assert body["exercises"][0]["sets"] == original["exercises"][0]["sets"]
        persisted = await api_client.get(detail_url, headers=headers)
        assert persisted.json()["exercises"][0]["notes"] == notes


@pytest.mark.parametrize(
    "payload", [{}, {"notes": 42}, {"notes": "Text", "position": 2}]
)
@pytest.mark.asyncio
async def test_patch_exercise_notes_validate_payload(
    api_client: AsyncClient, editable_set, payload: dict[str, object]
) -> None:
    headers, workout_id, _ = editable_set
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}/exercises/{uuid4()}",
        headers=headers,
        json=payload,
    )
    assert response.status_code == 422


@pytest.mark.parametrize("closed_status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_patch_exercise_notes_reject_closed_session(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, closed_status: str
) -> None:
    headers, workout_id, set_id = editable_set
    item = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = item.session_exercise_id
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = closed_status
    workout.completed_at = workout.started_at if closed_status == "completed" else None
    await db_session.commit()
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}/exercises/{exercise_id}",
        headers=headers,
        json={"notes": "Change"},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_patch_exercise_notes_auth_and_cross_session_isolation(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    other_headers, other_id = await login(api_client, "outsider")
    item = await db_session.get(WorkoutSessionSet, set_id)
    exercise_id = item.session_exercise_id
    foreign_exercise = WorkoutSessionExercise(
        position=0,
        exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []},
        notes="Keep",
    )
    db_session.add(
        WorkoutSession(user_id=other_id, name="Other", exercises=[foreign_exercise])
    )
    await db_session.commit()
    foreign_id = foreign_exercise.id
    cases = [
        ({}, workout_id, exercise_id, 401),
        (other_headers, workout_id, exercise_id, 404),
        (headers, workout_id, foreign_id, 404),
        (headers, workout_id, uuid4(), 404),
        (headers, uuid4(), exercise_id, 404),
    ]
    for auth, target_session, target_exercise, expected in cases:
        response = await api_client.patch(
            f"/workout-sessions/{target_session}/exercises/{target_exercise}",
            headers=auth,
            json={"notes": "Change"},
        )
        assert response.status_code == expected, response.text
    await db_session.refresh(foreign_exercise)
    assert foreign_exercise.notes == "Keep"


@pytest.mark.asyncio
async def test_patch_session_notes_persists_and_clears(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    url = f"/workout-sessions/{workout_id}"
    original = (await api_client.get(url, headers=headers)).json()
    for notes in ["Наступного разу легше", None]:
        response = await api_client.patch(url, headers=headers, json={"notes": notes})
        assert response.status_code == 200, response.text
        assert response.json() == {**original, "notes": notes}
        saved = await api_client.get(url, headers=headers)
        assert saved.json()["notes"] == notes


@pytest.mark.parametrize(
    "payload", [{}, {"notes": 42}, {"notes": "Text", "status": "completed"}]
)
@pytest.mark.asyncio
async def test_patch_notes_rejects_invalid_body(
    api_client: AsyncClient, editable_set, payload: dict[str, object]
) -> None:
    headers, workout_id, _ = editable_set
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}", headers=headers, json=payload
    )
    assert response.status_code == 422


@pytest.mark.parametrize("closed_status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_patch_notes_rejects_closed_workout(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, closed_status: str
) -> None:
    headers, workout_id, _ = editable_set
    workout = await db_session.get(WorkoutSession, workout_id)
    assert workout is not None
    workout.status = closed_status
    workout.completed_at = workout.started_at if closed_status == "completed" else None
    await db_session.commit()
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}", headers=headers, json={"notes": "Change"}
    )
    assert response.status_code == 409
    await db_session.refresh(workout)
    assert workout.notes is None


@pytest.mark.asyncio
async def test_patch_notes_requires_auth_and_hides_private_resources(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, _ = editable_set
    other_headers, _ = await login(api_client, "outsider")
    for auth, target, expected in [
        ({}, workout_id, 401),
        (other_headers, workout_id, 404),
        (headers, uuid4(), 404),
    ]:
        response = await api_client.patch(
            f"/workout-sessions/{target}", headers=auth, json={"notes": "Change"}
        )
        assert response.status_code == expected, response.text


@pytest_asyncio.fixture
async def editable_set(
    api_client: AsyncClient, db_session: AsyncSession
) -> tuple[dict[str, str], UUID, UUID]:
    headers, owner_id = await login(api_client, "editor")
    item = WorkoutSessionSet(position=0, set_type="working", planned_reps=10)
    workout = WorkoutSession(
        user_id=owner_id,
        name="Edit",
        exercises=[
            WorkoutSessionExercise(
                position=0,
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                sets=[item],
            )
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    return headers, workout.id, item.id


@pytest.mark.asyncio
async def test_patch_set_records_corrects_and_reopens(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    url = f"/workout-sessions/{workout_id}/sets/{set_id}"
    response = await api_client.patch(
        url,
        headers=headers,
        json={"actual_reps": 8, "actual_weight_kg": "62.50", "status": "completed"},
    )
    assert response.status_code == 200, response.text
    item = response.json()["exercises"][0]["sets"][0]
    completed_at = item["completed_at"]
    assert completed_at is not None
    assert item["planned_reps"] == 10 and item["actual_reps"] == 8
    response = await api_client.patch(url, headers=headers, json={"actual_reps": 9})
    assert response.status_code == 200
    item = response.json()["exercises"][0]["sets"][0]
    # SQLite drops timezone metadata when the timestamp is loaded again.
    assert datetime.fromisoformat(item["completed_at"]).replace(
        tzinfo=UTC
    ) == datetime.fromisoformat(completed_at).replace(tzinfo=UTC)
    assert item["actual_weight_kg"] == "62.50"
    response = await api_client.patch(
        url, headers=headers, json={"status": "pending", "actual_weight_kg": None}
    )
    assert response.status_code == 200
    item = response.json()["exercises"][0]["sets"][0]
    assert item["completed_at"] is None and item["actual_weight_kg"] is None
    assert item["actual_reps"] == 9


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"actual_reps": 0},
        {"actual_weight_kg": "-1"},
        {"status": None},
        {"planned_reps": 20},
    ],
)
@pytest.mark.asyncio
async def test_patch_set_rejects_invalid_payload(
    api_client: AsyncClient, editable_set, payload: dict[str, object]
) -> None:
    headers, workout_id, set_id = editable_set
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}/sets/{set_id}", headers=headers, json=payload
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_patch_set_rejects_completion_without_reps(
    api_client: AsyncClient, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}/sets/{set_id}",
        headers=headers,
        json={"status": "completed"},
    )
    assert response.status_code == 409


@pytest.mark.parametrize("closed_status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_patch_set_rejects_closed_workout(
    api_client: AsyncClient, db_session: AsyncSession, editable_set, closed_status: str
) -> None:
    headers, workout_id, set_id = editable_set
    workout = await db_session.get(WorkoutSession, workout_id)
    workout.status = closed_status
    workout.completed_at = workout.started_at if closed_status == "completed" else None
    await db_session.commit()
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}/sets/{set_id}",
        headers=headers,
        json={"actual_reps": 8},
    )
    assert response.status_code == 409


@pytest.mark.asyncio
async def test_patch_set_requires_authentication(
    api_client: AsyncClient, editable_set
) -> None:
    _, workout_id, set_id = editable_set
    response = await api_client.patch(
        f"/workout-sessions/{workout_id}/sets/{set_id}", json={"actual_reps": 8}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_patch_set_rejects_foreign_workout_and_mismatched_set(
    api_client: AsyncClient, db_session: AsyncSession, editable_set
) -> None:
    headers, workout_id, set_id = editable_set
    other_headers, other_id = await login(api_client, "outsider")
    other_set = WorkoutSessionSet(position=0, set_type="working")
    other_workout = WorkoutSession(
        user_id=other_id,
        name="Other",
        exercises=[
            WorkoutSessionExercise(
                position=0,
                exercise_snapshot={"names": {"en": "Other"}, "muscle_groups": []},
                sets=[other_set],
            )
        ],
    )
    db_session.add(other_workout)
    await db_session.commit()
    cases = [
        (other_headers, workout_id, set_id),
        (headers, workout_id, other_set.id),
        (headers, uuid4(), set_id),
        (headers, workout_id, uuid4()),
    ]
    for auth, session_id, target_set_id in cases:
        response = await api_client.patch(
            f"/workout-sessions/{session_id}/sets/{target_set_id}",
            headers=auth,
            json={"actual_reps": 8},
        )
        assert response.status_code == 404, response.text
    saved = await db_session.get(WorkoutSessionSet, set_id)
    assert saved.actual_reps is None


@pytest.mark.asyncio
async def test_template_start_and_read_http_flow(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _ = await login(api_client, "owner")
    db_session.add(MuscleGroup(code="quadriceps", names={"en": "Quadriceps"}))
    await db_session.commit()
    exercise = await api_client.post(
        "/exercises",
        headers=headers,
        json={
            "name": "Custom squat",
            "locale": "en",
            "muscle_group_codes": ["quadriceps"],
        },
    )
    assert exercise.status_code == 201, exercise.text
    template = await api_client.post(
        "/workout-templates",
        headers=headers,
        json={
            "name": "Leg day",
            "exercises": [
                {
                    "exercise_id": exercise.json()["id"],
                    "position": 0,
                    "notes": "Slow descent",
                    "sets": [
                        {
                            "position": 0,
                            "set_type": "working",
                            "target_reps": 8,
                            "target_weight_kg": "60.50",
                        }
                    ],
                }
            ],
        },
    )
    assert template.status_code == 201, template.text
    payload = {"template_id": template.json()["id"]}
    response = await api_client.post("/workout-sessions", headers=headers, json=payload)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["name"] == "Leg day"
    assert body["template_id"] == payload["template_id"]
    assert body["status"] == "in_progress"
    assert body["duration_seconds"] is None
    item = body["exercises"][0]
    assert item["notes"] == "Slow descent"
    assert item["exercise_snapshot"]["names"]["en"] == "Custom squat"
    assert item["sets"][0]["planned_reps"] == 8
    assert item["sets"][0]["planned_weight_kg"] == "60.50"
    assert item["sets"][0]["actual_reps"] is None
    for path in ["active", body["id"]]:
        read = await api_client.get(f"/workout-sessions/{path}", headers=headers)
        assert read.status_code == 200
        assert read.json() == body
    duplicate = await api_client.post(
        "/workout-sessions", headers=headers, json=payload
    )
    assert duplicate.status_code == 409
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 1
    )


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
@pytest.mark.asyncio
async def test_start_requires_authentication(
    api_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await api_client.post(
        "/workout-sessions", headers=headers, json={"template_id": str(uuid4())}
    )
    assert response.status_code == 401


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"template_id": "bad-id"},
        {"template_id": None},
        {"template_id": str(uuid4()), "user_id": str(uuid4())},
        {"template_id": str(uuid4()), "status": "completed"},
    ],
)
@pytest.mark.asyncio
async def test_start_rejects_invalid_request(
    api_client: AsyncClient, db_session: AsyncSession, payload: dict[str, object]
) -> None:
    headers, _ = await login(api_client, "owner")
    response = await api_client.post("/workout-sessions", headers=headers, json=payload)
    assert response.status_code == 422
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 0
    )


@pytest.mark.asyncio
async def test_start_rejects_missing_private_and_empty_templates(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, owner_id = await login(api_client, "owner")
    _, other_id = await login(api_client, "other")
    owned = WorkoutTemplate(user_id=owner_id, name="Empty")
    private = WorkoutTemplate(user_id=other_id, name="Private")
    db_session.add_all([owned, private])
    await db_session.commit()
    cases = [(owned.id, 409), (private.id, 404), (uuid4(), 404)]
    for template_id, expected in cases:
        response = await api_client.post(
            "/workout-sessions", headers=headers, json={"template_id": str(template_id)}
        )
        assert response.status_code == expected, response.text
    assert (
        await db_session.scalar(select(func.count()).select_from(WorkoutSession)) == 0
    )


@pytest.mark.parametrize("session_status", ["in_progress", "completed", "cancelled"])
@pytest.mark.asyncio
async def test_get_session_returns_owned_workout_in_any_state(
    api_client: AsyncClient, db_session: AsyncSession, session_status: str
) -> None:
    headers, owner_id = await login(api_client, "owner")
    start = datetime(2026, 9, 18, tzinfo=UTC)
    workout = WorkoutSession(
        user_id=owner_id,
        name="Owned workout",
        status=session_status,
        started_at=start,
        completed_at=start + timedelta(hours=1)
        if session_status == "completed"
        else None,
        exercises=[
            WorkoutSessionExercise(
                position=0,
                exercise_snapshot={"names": {"en": "Squat"}, "muscle_groups": []},
                sets=[
                    WorkoutSessionSet(position=0, set_type="working", planned_reps=8)
                ],
            )
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    workout_id = workout.id
    db_session.expunge_all()
    response = await api_client.get(f"/workout-sessions/{workout_id}", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(workout_id)
    assert body["status"] == session_status
    assert body["duration_seconds"] == (3600 if session_status == "completed" else None)
    assert body["exercises"][0]["sets"][0]["planned_reps"] == 8


@pytest.mark.asyncio
async def test_get_session_hides_private_and_missing_resources(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, _ = await login(api_client, "owner")
    _, other_id = await login(api_client, "other")
    workout = WorkoutSession(user_id=other_id, name="Private")
    db_session.add(workout)
    await db_session.commit()
    for resource_id in [workout.id, uuid4()]:
        response = await api_client.get(
            f"/workout-sessions/{resource_id}", headers=headers
        )
        assert response.status_code == 404
        assert response.json() == {"detail": "Workout session not found"}


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
@pytest.mark.asyncio
async def test_get_session_requires_authentication(
    api_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await api_client.get(f"/workout-sessions/{uuid4()}", headers=headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_session_rejects_invalid_uuid(api_client: AsyncClient) -> None:
    headers, _ = await login(api_client, "owner")
    response = await api_client.get("/workout-sessions/not-a-uuid", headers=headers)
    assert response.status_code == 422
    assert response.json()["detail"][0]["loc"] == ["path", "session_id"]


@pytest.fixture(autouse=True)
def fast_passwords(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_service, "hash_password", lambda password: "test-hash")
    monkeypatch.setattr(
        auth_service,
        "verify_password",
        lambda plain, hashed: plain == "strong-password" and hashed == "test-hash",
    )


async def login(client: AsyncClient, name: str) -> tuple[dict[str, str], UUID]:
    response = await client.post(
        "/auth/register",
        json={
            "email": f"{name}@example.com",
            "username": name,
            "first_name": "Session",
            "last_name": "Tester",
            "password": "strong-password",
        },
    )
    assert response.status_code == 201, response.text
    user_id = UUID(response.json()["id"])
    response = await client.post(
        "/auth/login",
        json={"login": f"{name}@example.com", "password": "strong-password"},
    )
    assert response.status_code == 200, response.text
    headers = {"Authorization": f"Bearer {response.json()['access_token']}"}
    return headers, user_id


@pytest.mark.parametrize("headers", [{}, {"Authorization": "Bearer invalid"}])
@pytest.mark.asyncio
async def test_active_workout_requires_authentication(
    api_client: AsyncClient, headers: dict[str, str]
) -> None:
    response = await api_client.get("/workout-sessions/active", headers=headers)
    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.asyncio
async def test_active_workout_returns_null_when_absent(api_client: AsyncClient) -> None:
    headers, _ = await login(api_client, "owner")
    response = await api_client.get("/workout-sessions/active", headers=headers)
    assert response.status_code == 200
    assert response.json() is None


@pytest.mark.asyncio
async def test_active_workout_returns_only_owned_ordered_tree(
    api_client: AsyncClient, db_session: AsyncSession
) -> None:
    headers, owner_id = await login(api_client, "owner")
    other_headers, other_id = await login(api_client, "other")
    workout = WorkoutSession(
        user_id=owner_id,
        name="Private workout",
        exercises=[
            WorkoutSessionExercise(
                position=position,
                exercise_snapshot={
                    "names": {"en": name, "uk": "Вправа"},
                    "muscle_groups": [],
                },
                sets=[
                    WorkoutSessionSet(
                        position=index, set_type="working", planned_reps=8
                    )
                    for index in [1, 0]
                ],
            )
            for position, name in [(1, "Squat"), (0, "Bench")]
        ],
    )
    db_session.add(workout)
    await db_session.commit()
    workout_id = workout.id
    response = await api_client.get("/workout-sessions/active", headers=other_headers)
    assert response.status_code == 200 and response.json() is None
    other = WorkoutSession(user_id=other_id, name="Other workout")
    db_session.add(other)
    await db_session.commit()
    other_workout_id = other.id
    db_session.expunge_all()

    response = await api_client.get("/workout-sessions/active", headers=headers)
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["id"] == str(workout_id)
    assert body["name"] == "Private workout"
    assert body["status"] == "in_progress"
    assert body["started_at"] is not None
    assert body["duration_seconds"] is None
    assert [item["position"] for item in body["exercises"]] == [0, 1]
    assert all(
        [entry["position"] for entry in item["sets"]] == [0, 1]
        for item in body["exercises"]
    )
    response = await api_client.get("/workout-sessions/active", headers=other_headers)
    assert response.status_code == 200
    assert response.json()["id"] == str(other_workout_id)


@pytest.mark.parametrize("status", ["completed", "cancelled"])
@pytest.mark.asyncio
async def test_active_workout_excludes_closed_sessions(
    api_client: AsyncClient, db_session: AsyncSession, status: str
) -> None:
    headers, owner_id = await login(api_client, "owner")
    start = datetime(2026, 9, 18, tzinfo=UTC)
    db_session.add(
        WorkoutSession(
            user_id=owner_id,
            name="Closed",
            status=status,
            started_at=start,
            completed_at=start + timedelta(hours=1) if status == "completed" else None,
        )
    )
    await db_session.commit()
    response = await api_client.get("/workout-sessions/active", headers=headers)
    assert response.status_code == 200
    assert response.json() is None

from httpx import AsyncClient


async def _create_user(client: AsyncClient, email: str = "requester@example.com") -> str:
    resp = await client.post("/users", json={"name": "Alice", "email": email})
    assert resp.status_code == 201
    return resp.json()["id"]


async def _create_sla_policies(client: AsyncClient) -> None:
    policies = [
        {"priority": "P1", "response_minutes": 15, "resolve_minutes": 240},
        {"priority": "P2", "response_minutes": 30, "resolve_minutes": 480},
        {"priority": "P3", "response_minutes": 240, "resolve_minutes": 2880},
        {"priority": "P4", "response_minutes": 1440, "resolve_minutes": 7200},
    ]
    for policy in policies:
        resp = await client.post("/sla-policies", json=policy)
        assert resp.status_code == 201


async def test_create_ticket_computes_priority_and_sla(client: AsyncClient) -> None:
    requester_id = await _create_user(client)
    await _create_sla_policies(client)

    resp = await client.post(
        "/tickets",
        json={
            "title": "VPN not connecting",
            "description": "Cannot connect to VPN since this morning",
            "impact": "High",
            "urgency": "High",
            "requester_id": requester_id,
        },
    )

    assert resp.status_code == 201
    ticket = resp.json()
    assert ticket["priority"] == "P1"
    assert ticket["status"] == "New"
    assert ticket["ticket_number"].startswith("TCK-")
    assert ticket["sla_response_due"] is not None
    assert ticket["sla_resolve_due"] is not None


async def test_create_ticket_without_sla_policy_has_no_due_dates(client: AsyncClient) -> None:
    requester_id = await _create_user(client)

    resp = await client.post(
        "/tickets",
        json={
            "title": "Minor request",
            "impact": "Low",
            "urgency": "Low",
            "requester_id": requester_id,
        },
    )

    assert resp.status_code == 201
    ticket = resp.json()
    assert ticket["priority"] == "P4"
    assert ticket["sla_response_due"] is None
    assert ticket["sla_resolve_due"] is None


async def test_valid_status_transition(client: AsyncClient) -> None:
    requester_id = await _create_user(client)
    resp = await client.post(
        "/tickets",
        json={"title": "Password reset", "impact": "Low", "urgency": "Low", "requester_id": requester_id},
    )
    ticket_id = resp.json()["id"]

    resp = await client.patch(f"/tickets/{ticket_id}", json={"status": "Triaged"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "Triaged"


async def test_invalid_status_transition_is_rejected(client: AsyncClient) -> None:
    requester_id = await _create_user(client)
    resp = await client.post(
        "/tickets",
        json={"title": "Password reset", "impact": "Low", "urgency": "Low", "requester_id": requester_id},
    )
    ticket_id = resp.json()["id"]

    # New -> Resolved is not an allowed direct transition.
    resp = await client.patch(f"/tickets/{ticket_id}", json={"status": "Resolved"})
    assert resp.status_code == 409


async def test_status_change_is_recorded_in_history(client: AsyncClient) -> None:
    requester_id = await _create_user(client)
    resp = await client.post(
        "/tickets",
        json={"title": "Password reset", "impact": "Low", "urgency": "Low", "requester_id": requester_id},
    )
    ticket_id = resp.json()["id"]

    await client.patch(f"/tickets/{ticket_id}", json={"status": "Triaged", "changed_by_id": requester_id})

    resp = await client.get(f"/tickets/{ticket_id}/history")
    assert resp.status_code == 200
    history = resp.json()
    assert len(history) == 1
    assert history[0]["field"] == "status"
    assert history[0]["old_value"] == "New"
    assert history[0]["new_value"] == "Triaged"


async def test_add_and_list_comments(client: AsyncClient) -> None:
    requester_id = await _create_user(client)
    resp = await client.post(
        "/tickets",
        json={"title": "Password reset", "impact": "Low", "urgency": "Low", "requester_id": requester_id},
    )
    ticket_id = resp.json()["id"]

    resp = await client.post(
        f"/tickets/{ticket_id}/comments",
        json={"author_id": requester_id, "body": "Any update?", "is_internal": False},
    )
    assert resp.status_code == 201

    resp = await client.get(f"/tickets/{ticket_id}/comments")
    assert resp.status_code == 200
    comments = resp.json()
    assert len(comments) == 1
    assert comments[0]["body"] == "Any update?"


async def test_list_tickets_filters_by_status(client: AsyncClient) -> None:
    requester_id = await _create_user(client)
    await client.post(
        "/tickets",
        json={"title": "Ticket A", "impact": "Low", "urgency": "Low", "requester_id": requester_id},
    )
    resp = await client.post(
        "/tickets",
        json={"title": "Ticket B", "impact": "Low", "urgency": "Low", "requester_id": requester_id},
    )
    await client.patch(f"/tickets/{resp.json()['id']}", json={"status": "Triaged"})

    resp = await client.get("/tickets", params={"status": "Triaged"})
    assert resp.status_code == 200
    tickets = resp.json()
    assert len(tickets) == 1
    assert tickets[0]["title"] == "Ticket B"


async def test_get_missing_ticket_returns_404(client: AsyncClient) -> None:
    resp = await client.get("/tickets/does-not-exist")
    assert resp.status_code == 404

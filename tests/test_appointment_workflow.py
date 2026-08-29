import asyncio
from uuid import UUID

import httpx

from appointment_assets.appointment_workflow import AppointmentAssetWorkflow, ConfirmationRequest
from appointment_assets.infrai_storage import InfraiStorage


class RecordedStorage:
    def __init__(self, found: bool) -> None:
        self.found = found

    async def presign_put(self, bucket: str, key: str, content_type: str, max_bytes: int, idempotency_key: str) -> dict:
        return {"url": "https://upload.example/signed"}

    async def head_object(self, bucket: str, key: str) -> dict:
        return {"found": self.found}


def test_notification_waits_until_the_asset_exists() -> None:
    appointment_id = UUID("bca49c75-dc4d-46f8-99bd-41120bd318a0")
    asset_id = UUID("2b27be08-f9c7-4c58-97c2-5c98296b6909")
    request = ConfirmationRequest(appointment_id=appointment_id, asset_id=asset_id)

    pending = asyncio.run(AppointmentAssetWorkflow(RecordedStorage(found=False), "appointment-assets").confirm_upload(request))
    ready = asyncio.run(AppointmentAssetWorkflow(RecordedStorage(found=True), "appointment-assets").confirm_upload(request))

    assert pending.model_dump() == {"state": "awaiting_upload", "notification": None}
    assert ready.model_dump() == {
        "state": "ready_for_review",
        "notification": "A requested appointment document is ready for staff review.",
    }


def test_bucket_cleanup_uses_encoded_discovery_paths() -> None:
    requests: list[tuple[str, bytes]] = []

    def respond(request: httpx.Request) -> httpx.Response:
        requests.append((request.method, request.url.raw_path))
        return httpx.Response(200, json={"ok": True, "data": {"found": request.method == "GET"}})

    async def exercise() -> None:
        storage = InfraiStorage(api_key="test", transport=httpx.MockTransport(respond))
        try:
            await storage.delete_bucket("appointment assets")
            await storage.get_bucket("appointment assets")
        finally:
            await storage.close()

    asyncio.run(exercise())

    assert requests == [
        ("DELETE", b"/v1/storage/bucket/delete/appointment%20assets"),
        ("GET", b"/v1/storage/bucket/get/appointment%20assets"),
    ]

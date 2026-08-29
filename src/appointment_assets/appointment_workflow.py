from typing import Any, Literal
from uuid import UUID

from pydantic import BaseModel, Field


class UploadRequest(BaseModel):
    appointment_id: UUID
    asset_id: UUID
    content_type: Literal["image/jpeg", "image/png", "application/pdf"]
    size_bytes: int = Field(gt=0, le=10_000_000)


class UploadTicket(BaseModel):
    appointment_id: UUID
    asset_id: UUID
    object_key: str
    upload_url: str
    method: Literal["PUT"] = "PUT"
    expires_seconds: int = 600


class ConfirmationRequest(BaseModel):
    appointment_id: UUID
    asset_id: UUID


class ConfirmationResult(BaseModel):
    state: Literal["awaiting_upload", "ready_for_review"]
    notification: str | None


class AppointmentAssetWorkflow:
    def __init__(self, storage: Any, bucket: str) -> None:
        self.storage = storage
        self.bucket = bucket

    @staticmethod
    def object_key(appointment_id: UUID, asset_id: UUID) -> str:
        return f"appointments/{appointment_id}/assets/{asset_id}"

    async def issue_upload(self, request: UploadRequest) -> UploadTicket:
        key = self.object_key(request.appointment_id, request.asset_id)
        signed = await self.storage.presign_put(
            self.bucket,
            key,
            request.content_type,
            request.size_bytes,
            f"appointment-asset:{request.asset_id}",
        )
        return UploadTicket(
            appointment_id=request.appointment_id,
            asset_id=request.asset_id,
            object_key=key,
            upload_url=signed["url"],
        )

    async def confirm_upload(self, request: ConfirmationRequest) -> ConfirmationResult:
        key = self.object_key(request.appointment_id, request.asset_id)
        head = await self.storage.head_object(self.bucket, key)
        if not head.get("found", False):
            return ConfirmationResult(state="awaiting_upload", notification=None)
        return ConfirmationResult(
            state="ready_for_review",
            notification="A requested appointment document is ready for staff review.",
        )

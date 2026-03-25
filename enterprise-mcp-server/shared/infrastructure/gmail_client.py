"""
Shared Gmail client abstraction.

AbstractGmailClient defines the interface all tools depend on.
GmailClient wraps the existing synchronous gmail_client.py using
asyncio.to_thread() so it does not block the async event loop.
StubGmailClient is for unit tests only — returns fixture dicts.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Any, Optional


# ---------------------------------------------------------------------------
# Abstract interface — 12 methods derived from tools_email.py
# ---------------------------------------------------------------------------

class AbstractGmailClient(ABC):

    @abstractmethod
    async def list_messages(
        self, user_id: str, max_results: int,
        q: Optional[str] = None,
        label_ids: Optional[list] = None,
    ) -> dict: ...

    @abstractmethod
    async def get_message(
        self, user_id: str, msg_id: str, fmt: str = "full"
    ) -> dict: ...

    @abstractmethod
    async def send_message(self, user_id: str, body: dict) -> dict: ...

    @abstractmethod
    async def list_threads(
        self, user_id: str, max_results: int,
        q: Optional[str] = None,
        label_ids: Optional[list] = None,
    ) -> dict: ...

    @abstractmethod
    async def get_thread(
        self, user_id: str, thread_id: str, fmt: str = "full"
    ) -> dict: ...

    @abstractmethod
    async def get_profile(self, user_id: str) -> dict: ...

    @abstractmethod
    async def create_draft(self, user_id: str, body: dict) -> dict: ...

    @abstractmethod
    async def list_drafts(
        self, user_id: str, max_results: int
    ) -> dict: ...

    @abstractmethod
    async def delete_draft(self, user_id: str, draft_id: str) -> None: ...

    @abstractmethod
    async def modify_message(
        self, user_id: str, msg_id: str, body: dict
    ) -> dict: ...

    @abstractmethod
    async def list_labels(self, user_id: str) -> dict: ...

    @abstractmethod
    async def get_attachment(
        self, user_id: str, message_id: str, att_id: str
    ) -> dict: ...


# ---------------------------------------------------------------------------
# Production implementation — wraps existing synchronous gmail_client.py
# ---------------------------------------------------------------------------

class GmailClient(AbstractGmailClient):
    """
    Wraps app.infrastructure.external.gmail_client using asyncio.to_thread().
    The existing OAuth, retry, and rate-limit logic is unchanged.
    Each method runs the synchronous Google API call in a thread pool
    so it does not block the FastMCP async event loop.
    """

    async def list_messages(
        self, user_id: str, max_results: int,
        q: Optional[str] = None,
        label_ids: Optional[list] = None,
    ) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            kwargs: dict = {"userId": user_id, "maxResults": max_results}
            if q:
                kwargs["q"] = q
            if label_ids:
                kwargs["labelIds"] = label_ids
            return execute_gmail_api(svc.users().messages().list(**kwargs))
        return await asyncio.to_thread(_sync)

    async def get_message(
        self, user_id: str, msg_id: str, fmt: str = "full"
    ) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            kwargs: dict = {"userId": user_id, "id": msg_id, "format": fmt}
            if fmt == "metadata":
                kwargs["metadataHeaders"] = ["From", "To", "Subject", "Date"]
            return execute_gmail_api(svc.users().messages().get(**kwargs))
        return await asyncio.to_thread(_sync)

    async def send_message(self, user_id: str, body: dict) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().messages().send(userId=user_id, body=body)
            )
        return await asyncio.to_thread(_sync)

    async def list_threads(
        self, user_id: str, max_results: int,
        q: Optional[str] = None,
        label_ids: Optional[list] = None,
    ) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            kwargs: dict = {"userId": user_id, "maxResults": max_results}
            if q:
                kwargs["q"] = q
            if label_ids:
                kwargs["labelIds"] = label_ids
            return execute_gmail_api(svc.users().threads().list(**kwargs))
        return await asyncio.to_thread(_sync)

    async def get_thread(
        self, user_id: str, thread_id: str, fmt: str = "full"
    ) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            kwargs: dict = {
                "userId": user_id, "id": thread_id, "format": fmt,
            }
            if fmt == "metadata":
                kwargs["metadataHeaders"] = ["Subject", "From", "Date"]
            return execute_gmail_api(svc.users().threads().get(**kwargs))
        return await asyncio.to_thread(_sync)

    async def get_profile(self, user_id: str) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().getProfile(userId=user_id)
            )
        return await asyncio.to_thread(_sync)

    async def create_draft(self, user_id: str, body: dict) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().drafts().create(userId=user_id, body=body)
            )
        return await asyncio.to_thread(_sync)

    async def list_drafts(self, user_id: str, max_results: int) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().drafts().list(
                    userId=user_id,
                    maxResults=min(max_results, 500),
                )
            )
        return await asyncio.to_thread(_sync)

    async def delete_draft(self, user_id: str, draft_id: str) -> None:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            execute_gmail_api(
                svc.users().drafts().delete(userId=user_id, id=draft_id)
            )
        await asyncio.to_thread(_sync)

    async def modify_message(
        self, user_id: str, msg_id: str, body: dict
    ) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().messages().modify(
                    userId=user_id, id=msg_id, body=body
                )
            )
        return await asyncio.to_thread(_sync)

    async def list_labels(self, user_id: str) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().labels().list(userId=user_id)
            )
        return await asyncio.to_thread(_sync)

    async def get_attachment(
        self, user_id: str, message_id: str, att_id: str
    ) -> dict:
        def _sync():
            from app.infrastructure.external.gmail_client import (
                get_gmail_service, execute_gmail_api,
            )
            svc = get_gmail_service()
            return execute_gmail_api(
                svc.users().messages().attachments().get(
                    userId=user_id, messageId=message_id, id=att_id
                )
            )
        return await asyncio.to_thread(_sync)


# ---------------------------------------------------------------------------
# Stub for unit tests — no OAuth, no network calls
# ---------------------------------------------------------------------------

class StubGmailClient(AbstractGmailClient):
    """
    Inject this in tests instead of GmailClient.
    Pass fixtures dict to constructor:
        stub = StubGmailClient({"messages": [...], "threads": [...]})
    """

    def __init__(self, fixtures: dict | None = None):
        self._f = fixtures or {}

    async def list_messages(self, user_id, max_results, q=None, label_ids=None):
        return {"messages": self._f.get("messages", []), "resultSizeEstimate": 0}

    async def get_message(self, user_id, msg_id, fmt="full"):
        return self._f.get("message", {"id": msg_id, "payload": {}, "labelIds": []})

    async def send_message(self, user_id, body):
        return {"id": "stub_msg_id", "threadId": "stub_thread_id", "labelIds": []}

    async def list_threads(self, user_id, max_results, q=None, label_ids=None):
        return {"threads": self._f.get("threads", []), "resultSizeEstimate": 0}

    async def get_thread(self, user_id, thread_id, fmt="full"):
        return self._f.get("thread", {"id": thread_id, "messages": []})

    async def get_profile(self, user_id):
        return self._f.get("profile", {"emailAddress": "test@example.com",
                                        "messagesTotal": 0, "threadsTotal": 0})

    async def create_draft(self, user_id, body):
        return {"id": "stub_draft_id", "message": {"id": "stub_msg_id"}}

    async def list_drafts(self, user_id, max_results):
        return {"drafts": self._f.get("drafts", []), "resultSizeEstimate": 0}

    async def delete_draft(self, user_id, draft_id):
        return None

    async def modify_message(self, user_id, msg_id, body):
        return {"id": msg_id, "labelIds": body.get("addLabelIds", [])}

    async def list_labels(self, user_id):
        return {"labels": self._f.get("labels", [])}

    async def get_attachment(self, user_id, message_id, att_id):
        return {"data": self._f.get("attachment_data", ""), "size": 0}

"""Inbox do consumidor (AC-004-05, P-020): deduplica por `id` de envelope num Redis próprio.

Guarda só o `id` e o estado (`processing` ou `done`), nunca conteúdo. Utilizador ACL limitado a
`inbox:ai-engine:*` (`infra/ai-engine-redis/start.sh`).
"""

from dataclasses import dataclass, field
from typing import Literal, Protocol

import redis.asyncio as redis
from redis.exceptions import RedisError

PREFIX = "inbox:ai-engine:"
DONE_TTL_SECONDS = 7 * 24 * 3600
ClaimState = Literal["new", "processing", "done"]


class Inbox(Protocol):
    async def claim(self, message_id: str, ttl_seconds: int) -> ClaimState:
        """`new`: é nossa; `done`: já processada; `processing`: rasto de um processamento interrompido."""
        ...

    async def mark_done(self, message_id: str) -> None: ...

    async def ping(self) -> bool: ...

    async def aclose(self) -> None: ...


@dataclass(frozen=True)
class RedisSettings:
    host: str
    port: int
    user: str
    # repr=False: a password nunca aparece em logs, tracebacks nem no repr.
    password: str = field(repr=False)


class RedisInbox:
    def __init__(self, settings: RedisSettings) -> None:
        self._redis = redis.Redis(
            host=settings.host,
            port=settings.port,
            username=settings.user,
            password=settings.password,
            socket_timeout=5,
            socket_connect_timeout=5,
            decode_responses=True,
            # Sem CLIENT SETINFO: o utilizador ACL só tem os comandos da inbox.
            lib_name=None,
            lib_version=None,
        )

    async def claim(self, message_id: str, ttl_seconds: int) -> ClaimState:
        key = PREFIX + message_id
        for _ in range(2):
            if await self._redis.set(key, "processing", nx=True, ex=ttl_seconds):
                return "new"
            state = await self._redis.get(key)
            if state == "done":
                return "done"
            if state == "processing":
                return "processing"
            # A chave expirou entre o SET e o GET: tenta outra vez.
        return "processing"

    async def mark_done(self, message_id: str) -> None:
        await self._redis.set(PREFIX + message_id, "done", ex=DONE_TTL_SECONDS)

    async def ping(self) -> bool:
        try:
            return bool(await self._redis.ping())
        except RedisError, OSError:
            return False

    async def aclose(self) -> None:
        await self._redis.aclose()

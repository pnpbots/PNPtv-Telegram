# -*- coding: utf-8 -*-
"""Utility class for broadcasting messages to users."""

from __future__ import annotations

import asyncio
from datetime import datetime, timedelta, timezone
from typing import List, Optional
import logging

from telegram import Bot

from bot.subscriber_manager import subscriber_manager
from bot.config import BOT_TOKEN


logger = logging.getLogger(__name__)


class BroadcastManager:
    """Manage broadcasts with optional scheduling and segmentation."""

    def __init__(self, bot: Bot | None = None):
        self.bot = bot or Bot(token=BOT_TOKEN)
        self.scheduled: List[tuple[datetime, asyncio.Task]] = []

    async def send(
        self,
        text: Optional[str] = None,
        parse_mode: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        animation: Optional[str] = None,
        language: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> None:
        """Send a broadcast to users filtered by language and status."""
        users = await subscriber_manager.get_users(language=language, statuses=statuses)
        for user in users:
            try:
                if photo:
                    await self.bot.send_photo(
                        chat_id=user["user_id"],
                        photo=photo,
                        caption=text,
                        parse_mode=parse_mode,
                    )
                elif video:
                    await self.bot.send_video(
                        chat_id=user["user_id"],
                        video=video,
                        caption=text,
                        parse_mode=parse_mode,
                    )
                elif animation:
                    await self.bot.send_animation(
                        chat_id=user["user_id"],
                        animation=animation,
                        caption=text,
                        parse_mode=parse_mode,
                    )
                elif text:
                    await self.bot.send_message(
                        chat_id=user["user_id"],
                        text=text,
                        parse_mode=parse_mode,
                    )
            except Exception as exc:
                logger.error("Error broadcasting to %s: %s", user["user_id"], exc)

    def schedule(
        self,
        when: datetime,
        *,
        text: Optional[str] = None,
        parse_mode: Optional[str] = None,
        photo: Optional[str] = None,
        video: Optional[str] = None,
        animation: Optional[str] = None,
        language: Optional[str] = None,
        statuses: Optional[List[str]] = None,
    ) -> None:
        """Schedule a broadcast message."""
        now = datetime.now(timezone.utc)
        if when < now or when > now + timedelta(hours=72):
            raise ValueError("Broadcast time must be within 72 hours")
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        day_end = day_start + timedelta(hours=24)
        count = sum(bool(day_start <= t < day_end))
        if count >= 12:
            raise ValueError("Maximum 12 scheduled messages per 24h")

        async def _task():
            delay = (when - datetime.now(timezone.utc)).total_seconds()
            if delay > 0:
                await asyncio.sleep(delay)
            await self.send(
                text=text,
                parse_mode=parse_mode,
                photo=photo,
                video=video,
                animation=animation,
                language=language,
                statuses=statuses,
            )

        task = asyncio.create_task(_task())
        self.scheduled.append((when, task))

        def _remove_done_task(t):
            self.scheduled = [
                (w, tk) for (w, tk) in self.scheduled if tk is not t
            ]

        task.add_done_callback(_remove_done_task)

        def _cleanup(fut: asyncio.Task) -> None:
            self.scheduled = [
                (w, t) for (w, t) in self.scheduled if t is not fut
            ]

        task.add_done_callback(_cleanup)


broadcast_manager = BroadcastManager()

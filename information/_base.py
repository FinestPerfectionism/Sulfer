from collections.abc import Sequence
from pathlib import Path
from typing import Self, cast

from discord import AllowedMentions, HTTPException, TextChannel, Thread

from bot import Sulfer, log
from bot.ui import (
    ActionRow,
    Button,
    ButtonSection,
    Container,
    HiddenSmallSeparator,
    LayoutView,
    TextDisplay,
    VisibleLargeSeparator,
    VisibleSmallSeparator,
    link,
)
from constants import COG_EMOJI
from core.utilities import format_now, format_values

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Guild Information Base
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def _to_mentions(author_ids : list[int]) -> list[str]:
    return [f"<@{author_id}>" for author_id in author_ids]

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# load_text
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


def load_text(name : str, relative : str) -> str:
    path = Path(relative).parent / name

    try:
        return path.read_text(encoding = "utf-8")
    except FileNotFoundError:
        return f"Text from '{name}' not found. :["

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# ensure_views
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


async def ensure_views(
    bot        : Sulfer,
    channel_id : int,
    views      : Sequence[LayoutView],
) -> None:
    log.info("Starting view ensurement for channel: %s", channel_id)
    channel = bot.get_channel(channel_id)

    if channel is None:
        channel = await bot.fetch_channel(channel_id)

    if not isinstance(channel, TextChannel | Thread):
        error = f"{channel_id} is not a text channel or thread."
        raise TypeError(error)

    cursor = await bot.db.execute(
       t"""
        SELECT message_id
        FROM Information
        WHERE channel_id = {str(channel_id)}
        ORDER BY position
        """,
    )

    rows = await cursor.fetchall()
    await cursor.close()

    message_ids = [int(cast("int | str", row[0])) for row in rows]

    if len(message_ids) == len(views):
        for message_id in message_ids:
            try:
                await channel.fetch_message(message_id)
            except HTTPException:
                break
        else:
            message_count = 0

            async for _ in channel.history(limit = None):
                message_count += 1

            if message_count == len(views):
                log.info("View ensurement finished. No changes needed for channel: %s", channel_id)
                return

    async for message in channel.history(limit = None):
        try:
            await message.delete()
        except HTTPException:
            log.exception(
                "Failed to delete message %s in #%s.",
                message.id,
                channel.id,
            )

    new_message_ids : list[int] = []

    for view in views:
        message = await channel.send(view = view, allowed_mentions = AllowedMentions.none())

        new_message_ids.append(message.id)

    await bot.db.execute(
       t"""
        DELETE FROM Information
        WHERE channel_id = {str(channel_id)}
        """,
    )

    await bot.db.executemany(
        [
           t"""
            shelINSERT INTO Information (
                channel_id,
                position,
                message_id
            )
            VALUES ({channel_id}, {position}, {message_id})
            """ for position, message_id in enumerate(new_message_ids)
        ],
    )

    await bot.db.commit()
    log.info("View alignment finished. Rebuilt views for channel: %s", channel_id)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# TOS Button
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class TOSButton(Button[LayoutView]):
    def __init__(self) -> None:
        super().__init__(
            url   = "https://discord.com/terms",
            style = link,
            label = "Discord Terms of Service",
            emoji = COG_EMOJI,
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Info Header Section
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class InfoHeaderSection(LayoutView):
    def __init__(self, *, title : str, description : str, note : str | None = None) -> None:
        super().__init__()

        note_line = f"-# **Note:** {note}." if note else ""

        self.add_item(
            Container(
                TextDisplay(
                    f"# Welcome to {title}!\n"
                    f"{description}.\n"
                    f"{note_line}",
                ),
            ),
        )

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Info Primary Section
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class InfoPrimarySection(LayoutView):
    def __init__(
        self,
        *,
        title   : str,
        text    : str                | None = None,
        note    : str                | None = None,
        authors : list[int]          | None = None,
        button  : Button[LayoutView] | None = None,
    ) -> None:
        super().__init__(timeout = None)

        if note is None and authors is not None:
            note = (
                "-# All below is subject to change at any time based on Directorate decision or structural updates.\n"
               f"-# Assembled by the Directorate team. Primarily written by {format_values(_to_mentions(authors))}.\n"
            )

        self.container      : Container[LayoutView]        =  Container()
        self.last_added_row : ActionRow[LayoutView] | None = None

        if button:
            self.container.add_item(ButtonSection(f"# {title}", button = button))
            header_text = ""
        else:
            header_text = f"# {title}\n\n"

        self.container.add_text(
            f"{header_text}"
            f"{title} last updated {format_now("F")}.\n"
            f"{note}",
        )

        self.container.add_items(
            HiddenSmallSeparator(),
            VisibleSmallSeparator(),
            HiddenSmallSeparator(),
        )

        if text:
            self.container.add_text(text)

        self.add_item(self.container)

    def add_info(self, text : str) -> None:
        if self.last_added_row:
            self.container.add_item(VisibleLargeSeparator())
            self.last_added_row = None

        self.container.add_text(text)

    def add_row(self, row : ActionRow[LayoutView]) -> None:
        if len(self.container.children) > 0 and self.last_added_row is None:
            self.container.add_item(VisibleLargeSeparator())

        self.container.add_item(row)
        self.last_added_row = row

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Info Secondary Section
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class InfoSecondarySection(LayoutView):
    def __init__(self, *, text : str | None = None) -> None:
        super().__init__(timeout = None)

        self.container      : Container[LayoutView]        = Container()
        self.last_added_row : ActionRow[LayoutView] | None = None

        if text:
            self.container.add_text(text)

        self.add_item(self.container)

    def add_info(self, text : str) -> None:
        if self.last_added_row:
            self.container.add_item(VisibleLargeSeparator())
            self.last_added_row = None

        self.container.add_text(text)

    def add_row(self, row : ActionRow[LayoutView]) -> None:
        if len(self.container.children) > 0 and self.last_added_row is None:
            self.container.add_item(VisibleLargeSeparator())

        self.container.add_item(row)
        self.last_added_row = row

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Info Support Section
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class InfoSupportSection(LayoutView):
    def __init__(
        self,
        *,
        title       : str,
        description : str,
        text        : str,
        note        : str,
        footer      : str,
        button      : Button[LayoutView] | None,
    ) -> None:
        super().__init__(timeout = None)

        description_text : ButtonSection[LayoutView] | TextDisplay[Self]
        if button:
            description_text = ButtonSection(f"{description}.", button = button)
        else:
            description_text = TextDisplay(f"{description}.")

        self.add_item(
            Container(
                ButtonSection(f"# {title}", button = TOSButton()),
                description_text,
                HiddenSmallSeparator(),
                VisibleSmallSeparator(),
                HiddenSmallSeparator(),
                TextDisplay(
                    f"{text}.\n\n"
                    f"**Note:** {note}.\n\n"
                    f"{footer}.",
                ),
            ),
        )

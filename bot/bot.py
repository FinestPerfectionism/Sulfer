# pyright: reportImportCycles = false

# ⸻ It's going to complain about 'Interaction'.


from asyncio import to_thread
from contextlib import suppress
from inspect import getsource
from io import BytesIO
from logging import getLogger as get_logger
from pathlib import Path
from types import (
    CodeType,
    FrameType,
    FunctionType,
    MethodType,
    ModuleType,
    TracebackType,
)
from typing import Self, TypedDict, Unpack, cast, final, override

from discord import Embed, File, Guild, Intents, Message, Status, User
from discord import Interaction as BaseInteraction
from discord.ext import commands
from discord.ext.commands import (  # pyright: ignore[reportMissingTypeStubs]
    Context as BaseContext,
)
from discord.ext.commands.view import (  # pyright: ignore[reportMissingTypeStubs]
    StringView,
)
from discord.http import Route

from constants import DENIED_EMOJI, DEVELOPER_IDS, DisplayNameEffect, DisplayNameFont
from core.cog_loader import discover_cogs
from core.state import Connection, connect

from .types import LambdaInter, NameStyleResult
from .ui import Button, LayoutView, Modal, View, button

InspectableObject = (
    ModuleType
    | type
    | MethodType
    | FunctionType
    | TracebackType
    | FrameType
    | CodeType
)

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Bot & Client Management
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


log = get_logger("Sulfer")

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Context and Interaction Classes
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class _ContextKwargs(TypedDict, total = False):
    message : Message
    bot     : Sulfer
    view    : StringView


class _ContextClass(BaseContext["Sulfer"]):
    def __init__(self, **kwargs : Unpack[_ContextKwargs]) -> None:
        super().__init__(**kwargs)

    async def send_button(self, callback : LambdaInter, /) -> Message:
        @final
        class _ViewButton(View):
            def __init__(self, view_callback : LambdaInter, /) -> None:
                super().__init__(timeout = None)
                self.callback = view_callback

            @button(label = "Click me!")
            async def btn_basic(self, interaction : Interaction, _button : Button[Self]) -> None:
                try:
                    await self.callback(interaction)
                except Exception as e:
                    if not interaction.response.is_done():
                        await interaction.response.send_message(
                           f"{DENIED_EMOJI} **Error! :[**\n"
                            "```py\n"
                           f"{e}\n"
                            "```",
                            ephemeral = True,
                        )
                    else:
                        await interaction.followup.send(
                           f"{DENIED_EMOJI} **Error! :[**\n"
                            "```py\n"
                           f"{e}\n"
                            "```",
                            ephemeral = True,
                        )

        return await self.send(view = _ViewButton(callback))

    async def send_embed(self, embed : Embed, /) -> Message:
        return await self.send(embed = embed)

    async def send_view(self, view : View | LayoutView, /) -> Message:
        return await self.send(view = view)

    async def send_modal(self, modal : Modal, /) -> Message:
        async def func(interaction : Interaction) -> None:
            await interaction.response.send_modal(modal)

        return await self.send_button(func)

    async def show_attrs(
        self,
        target   : object,
        /,
        *,
        tall     : bool | None = None,
        dunders  : bool        = False,
        privates : bool        = False,
    ) -> Message:
        def _filter(attr : str) -> bool:
            if attr.startswith("__") and attr.endswith("__"):
                return dunders
            if attr.startswith("_"):
                return privates
            return True

        attrs = [attr for attr in dir(target) if _filter(attr)]

        if tall is None:
            estimated_length = sum(len(a) for a in attrs) + (2 * (len(attrs) - 1))
            tall = estimated_length > 80

        joiner = ",\n" if tall else ", "

        return await self.send(
            "```py"
           f"{joiner.join(attrs)}"
            "```",
        )

    async def show_def(self, target : InspectableObject, /) -> Message:
        source = getsource(target)
        msg    = (
            "```py\n"
           f"{source}\n"
            "```"
        )

        if len(msg) < 2000:
            return await self.send(msg)

        module   = getattr(target, "__module__", "global").replace(".", "/")
        qualname = getattr(target, "__qualname__", "object").replace(".", "/")
        filename = f"{module}/{qualname}.py"
        return await self.send(file = File(BytesIO(source.encode()), filename = filename))

    async def reference_delete(self) -> None:
        if self.message.reference and self.message.reference.message_id:
            with suppress(Exception):
                reference_message = await self.channel.fetch_message(self.message.reference.message_id)
                await reference_message.delete()


type Context              = _ContextClass
type Interaction          = BaseInteraction[Sulfer]
type ContextOrInteraction = Interaction | Context

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Sulfer Class
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
class Sulfer(commands.Bot):
    def __init__(self) -> None:
        super().__init__(
            chunk_guilds_at_startup = True,
            case_insensitive        = True,
            command_prefix          = commands.when_mentioned_or("-"),
            help_command            = None,
            intents                 = Intents.all(),
            status                  = Status.online,
        )
        self.version : float = 1.0

        self.db : Connection

        self.restarting : bool = False

        self.developers : list[User] = []

    @property
    def id(self) -> int | None:
        return self.user.id if self.user else None

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Name Styles
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    async def set_name_style(
        self,
        guild     : Guild,
        /,
        *,
        font_id   : DisplayNameFont,
        effect_id : DisplayNameEffect,
        colors    : list[str],
    ) -> None:
        color_integers = [int(hex_code, 16) for hex_code in colors]

        await self.http.request(
            route = Route("PATCH", "/guilds/{guild_id}/members/@me", guild_id = guild.id),
            json  = {
                "display_name_font_id"   : font_id.value,
                "display_name_effect_id" : effect_id.value,
                "display_name_colors"    : color_integers,
            },
        )

    async def get_name_style(self, guild : Guild, /) -> NameStyleResult | None:
        class NameStylePayload(TypedDict):
            font_id   : int
            effect_id : int
            colors    : list[int]

        class MemberNameStylePayload(TypedDict):
            display_name_styles : NameStylePayload

        # ⸻ self.user is never None, but pyright will complain anyway.

        if self.user is None:
            return None

        response = cast(
            "MemberNameStylePayload",
            await self.http.request(
                route = Route(
                    "GET", "/guilds/{guild_id}/members/{user_id}",
                    guild_id = guild.id,
                    user_id  = self.user.id,
                ),
            ),
        )

        styles = response["display_name_styles"]

        return NameStyleResult(
            font_id   = DisplayNameFont(styles["font_id"]),
            effect_id = DisplayNameEffect(styles["effect_id"]),
            colors    = [f"{color:06x}" for color in styles["colors"]],
        )

    async def reset_name_style(self, guild : Guild, /, *, branded : bool = True) -> None:

        # ⸻ Branded is the bot's special scheme instead of a normal discord font.

        await self.set_name_style(
            guild,
            font_id   = DisplayNameFont.cherry_bomb if branded else DisplayNameFont.default,
            effect_id = DisplayNameEffect.gradient  if branded else DisplayNameEffect.solid,
            colors    = ["000000", "FFFFFF"]        if branded else ["FFFFFF", "FFFFFF"],
        )

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # Custom Context
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def get_context[ContextT : BaseContext[Sulfer]](
        self,
        origin : Message        | BaseInteraction,
        *,
        cls    : type[ContextT] | None = None,
    ) -> ContextT | Context:
        return await super().get_context(origin, cls = cls or _ContextClass)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # setup_hook
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def setup_hook(self) -> None:
        if self.user:
            log.info("Logging in as %s, %s", self.user.name, self.user.id)

        self.developers = [user for developer_id in DEVELOPER_IDS if (user := await self.fetch_user(developer_id))]

        # ⸻ AIOSQLite

        db_path = Path("data/database.db")
        db_path.parent.mkdir(parents = True, exist_ok = True)

        self.db = await connect(str(db_path))

        def read_schema() -> str:
            return Path("schemas/information.sql").read_text(encoding = "utf-8")

        schema = await to_thread(read_schema)
        await self.db.executescript(schema)
        await self.db.commit()

        # ⸻ Cogs

        cogs = await to_thread(
            discover_cogs,
            "commands",
            "systems",
            "core",
        )

        for cog in cogs:
            try:
                await self.load_extension(cog)
                log.info("Loaded cog %s", cog)
            except Exception:
                log.exception("Failed to load cog %s", cog)

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # close
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @override
    async def close(self) -> None:
        if self.db:
            await self.db.close()

        await super().close()

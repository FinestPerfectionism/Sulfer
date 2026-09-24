from typing import final

from discord.app_commands import Choice, autocomplete, command, describe, guild_only
from discord.ext import commands

from bot import Interaction, Sulfer

from .ensure import run_information_ensure

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Information Group Commands
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


@final
@guild_only
class InformationCommands(
    commands.GroupCog,
    name        = "information",
    description = "Staff only —— Iinformation management commands.",
):
    def __init__(self, bot : Sulfer) -> None:
        super().__init__()
        self.bot = bot

    async def _piece_autocomplete(self, _interaction : Interaction, _current : str) -> list[Choice[str]]:
        ...

    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
    # /information ensure Command
    # ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻

    @command(
        name        = "ensure",
        description = "Ensure support guild information exists and in proper order.",
    )
    @autocomplete(piece = _piece_autocomplete)
    @describe(
        piece   = "The information piece to ensure. Defaults to every information piece.",
        whether = "Whether to force ensurement or not by sending the information regardless of whether it already exists or not.",
    )
    async def cmd_information_ensure(
        self,
        interaction : Interaction,
        *,
        force       : bool,
        piece       : str | None = None,
    ) -> None:
        await run_information_ensure(
            interaction = interaction,
            force       = force,
            piece       = piece,
        )


async def setup(bot : Sulfer) -> None:
    cog = InformationCommands(bot)
    await bot.add_cog(cog)

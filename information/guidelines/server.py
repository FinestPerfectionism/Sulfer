from constants import FINESTPERFECTIONISM_ID

from ._base import InfoHeaderSection, InfoPrimarySection, TOSButton, load_text

# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻
# Server Guidelines
# ⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻⸻


class ServerGuidelines1(InfoHeaderSection):
    def __init__(self) -> None:
        super().__init__(
            title       = "Cordex",
            description = "The support server for **BotWorks' Cordex**",
            note        = "It is within moderators' discretion as to whether you are breaking rules regardless of if the rules they find you to be breaking are listed here",
        )


class ServerGuidelines2(InfoPrimarySection):
    def __init__(self) -> None:
        super().__init__(
            title   = "Rules",
            text    = load_text("server.txt", __file__),
            authors = [FINESTPERFECTIONISM_ID],
            button  = TOSButton(),
        )

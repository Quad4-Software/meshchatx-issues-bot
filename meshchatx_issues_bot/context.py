from dataclasses import dataclass

from lxmfy import LXMFBot

from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.store import BlockStore, IssueStore


@dataclass
class AppContext:
    bot: LXMFBot
    settings: Settings
    issues: IssueStore
    blocks: BlockStore
    icon_field: object | None

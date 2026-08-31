import os
from dataclasses import dataclass


def _env(key: str, default: str = "") -> str:
    return os.environ.get(key, default).strip()


def _env_int(key: str, default: int) -> int:
    raw = _env(key)
    if not raw:
        return default
    return int(raw)


def _env_stamp_cost(key: str, default: int) -> int | None:
    raw = os.environ.get(key)
    if raw is None:
        value = default
    else:
        stripped = raw.strip().lower()
        if stripped in ("", "0", "none", "off", "false"):
            return None
        value = int(stripped)
    if value < 1:
        return None
    if value >= 255:
        return 254
    return value


def _env_bool(key: str, default: bool) -> bool:
    raw = _env(key)
    if not raw:
        return default
    return raw.lower() in ("1", "true", "yes", "on")


def _parse_admin_names(raw: str) -> dict[str, str]:
    from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash

    out: dict[str, str] = {}
    for part in raw.split(","):
        piece = part.strip()
        if ":" not in piece:
            continue
        hash_part, name = piece.split(":", 1)
        h = normalize_lxmf_hash(hash_part.strip())
        name = name.strip()
        if h and name:
            out[h] = name
    return out


def _parse_hashes(raw: str) -> frozenset[str]:
    from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash

    out: set[str] = set()
    for part in raw.split(","):
        h = normalize_lxmf_hash(part.strip())
        if h:
            out.add(h)
    return frozenset(out)


@dataclass(frozen=True)
class Settings:
    bot_name: str
    command_prefix: str | None
    admin_hashes: frozenset[str]
    notify_hashes: frozenset[str]
    announce_seconds: int
    announce_immediately: bool
    storage_path: str
    reticulum_config_dir: str | None
    rate_limit: int
    cooldown: int
    first_message_enabled: bool
    cmd_report: str
    cmd_update: str
    cmd_myissues: str
    cmd_issue: str
    cmd_issues: str
    cmd_close: str
    cmd_block: str
    cmd_unblock: str
    cmd_blocked: str
    list_issues_limit: int
    max_issue_body: int
    forward_attachments: bool
    max_attachments_per_issue: int
    max_attachment_bytes: int
    stamp_cost: int | None
    grant_admin_tickets: bool
    ticket_recipients: frozenset[str]
    admin_display_names: dict[str, str]
    require_identity_verification: bool
    test_mode: bool

    def admin_display_name(self, admin_hash: str) -> str:
        from meshchatx_issues_bot.identity import display_name_for_address

        return display_name_for_address(admin_hash, self)

    @classmethod
    def from_env(cls) -> "Settings":
        admins = _parse_hashes(_env("ADMIN_LXMF"))
        notify_raw = _env("NOTIFY_LXMF")
        notify = _parse_hashes(notify_raw) if notify_raw else admins
        ticket_recipients = frozenset(set(admins) | set(notify))

        prefix_raw = os.environ.get("COMMAND_PREFIX")
        if prefix_raw is None:
            command_prefix: str | None = "/"
        elif prefix_raw.strip() == "":
            command_prefix = None
        else:
            command_prefix = prefix_raw

        reticulum = _env("RETICULUM_CONFIG_DIR") or None

        return cls(
            bot_name=_env("BOT_NAME", "MeshChatX Issues"),
            command_prefix=command_prefix,
            admin_hashes=admins,
            notify_hashes=notify,
            announce_seconds=_env_int("ANNOUNCE_SECONDS", 600),
            announce_immediately=_env_bool("ANNOUNCE_IMMEDIATELY", True),
            storage_path=_env("STORAGE_PATH", "data"),
            reticulum_config_dir=reticulum,
            rate_limit=_env_int("RATE_LIMIT", 10),
            cooldown=_env_int("COOLDOWN", 30),
            first_message_enabled=_env_bool("FIRST_MESSAGE_ENABLED", True),
            cmd_report=_env("CMD_REPORT", "report"),
            cmd_update=_env("CMD_UPDATE", "update"),
            cmd_myissues=_env("CMD_MYISSUES", "myissues"),
            cmd_issue=_env("CMD_ISSUE", "issue"),
            cmd_issues=_env("CMD_ISSUES", "issues"),
            cmd_close=_env("CMD_CLOSE", "close"),
            cmd_block=_env("CMD_BLOCK", "block"),
            cmd_unblock=_env("CMD_UNBLOCK", "unblock"),
            cmd_blocked=_env("CMD_BLOCKED", "blocked"),
            list_issues_limit=_env_int("LIST_ISSUES_LIMIT", 20),
            max_issue_body=_env_int("MAX_ISSUE_BODY", 4000),
            forward_attachments=_env_bool("FORWARD_ATTACHMENTS", True),
            max_attachments_per_issue=_env_int("MAX_ATTACHMENTS_PER_ISSUE", 5),
            max_attachment_bytes=_env_int("MAX_ATTACHMENT_BYTES", 5_242_880),
            stamp_cost=_env_stamp_cost("STAMP_COST", 8),
            grant_admin_tickets=_env_bool("GRANT_ADMIN_TICKETS", True),
            ticket_recipients=ticket_recipients,
            admin_display_names=_parse_admin_names(_env("ADMIN_NAMES")),
            require_identity_verification=_env_bool(
                "REQUIRE_IDENTITY_VERIFICATION",
                True,
            ),
            test_mode=_env_bool("TEST_MODE", False),
        )

    def cmd(self, name: str) -> str:
        if self.command_prefix is None:
            return name
        return f"{self.command_prefix}{name}"

    def validate(self) -> list[str]:
        warnings: list[str] = []
        if not self.notify_hashes:
            warnings.append(
                "NOTIFY_LXMF / ADMIN_LXMF is empty; no admins will receive reports.",
            )
        if not self.admin_hashes:
            warnings.append("ADMIN_LXMF is empty; admin commands will be unusable.")
        return warnings

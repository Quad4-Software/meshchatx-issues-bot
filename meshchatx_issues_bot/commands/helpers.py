from meshchatx_issues_bot.context import AppContext
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash


def reply(ctx, app: AppContext, text: str) -> None:
    kwargs = {}
    if app.icon_field is not None:
        kwargs["lxmf_fields"] = app.icon_field
    ctx.reply(text, **kwargs)


def sender_hash(ctx) -> str | None:
    return normalize_lxmf_hash(ctx.sender)


def parse_report_body(args: list[str]) -> str | None:
    text = " ".join(args).strip()
    return text if text else None


def parse_update_args(args: list[str]) -> tuple[int, str] | None:
    if not args:
        return None
    try:
        issue_id = int(args[0])
    except ValueError:
        return None
    text = " ".join(args[1:]).strip()
    return issue_id, text


def title_from_body(body: str, max_len: int = 80) -> str:
    first = body.strip().split("\n")[0].strip()
    if not first:
        return "Issue report"
    if len(first) <= max_len:
        return first
    return first[: max_len - 3] + "..."

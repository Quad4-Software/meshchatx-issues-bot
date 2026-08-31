# MeshChatX Issues Bot

A LXMFy bot that allows users to file issues over LXMF.

Built with [LXMFy](https://lxmfy.quad4.io/).

## Requirements

- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- Reticulum configured (e.g. `~/.reticulum/config`)

## Setup

```bash
cp .env.example .env
# Set ADMIN_LXMF (and optionally NOTIFY_LXMF) to comma-separated 32-char LXMF hashes
uv sync
```

The bot loads `.env` from the current working directory (or next to the project) on startup. Shell exports override `.env` values.

## Run

```bash
uv run meshchatx-issues-bot
```

The bot prints its LXMF address on startup. Message that address from MeshChatX, Sideband, or another LXMF client.

## Configuration

Most behavior is controlled via environment variables. See `.env.example` for the full list.

| Variable | Purpose |
|----------|---------|
| `BOT_NAME` | Display name on the network |
| `COMMAND_PREFIX` | `/` by default; leave empty for no prefix |
| `ADMIN_LXMF` | Admins (commands + optional notifications) |
| `NOTIFY_LXMF` | Who receives new reports (defaults to `ADMIN_LXMF`) |
| `CMD_*` | Rename commands without changing code |
| `STAMP_COST` | LXMF stamps required to message the bot (default `8`, `0` disables) |
| `GRANT_ADMIN_TICKETS` | Give `ADMIN_LXMF` / `NOTIFY_LXMF` reply tickets so they can message without stamping |

## Commands

**Users:** `report`, `update`, `myissues`, `issue`, `whoami`
**Admins:** `issues`, `close`, `block`, `unblock`, `blocked`

Example: `/report Cannot reach settings after update`

Use `/update <id> [more text]` on an open issue to append text and/or attach more files to the same message. Updates notify admins with only the new content and new attachments.

Attach files, images, or audio to the same LXMF message as `report` or `update`; they are stored and forwarded to admins (see `FORWARD_ATTACHMENTS` and size limits in `.env.example`).

After a report, the user receives their LXMF hash and an issue id. Admins receive the full report including the reporter’s LXMF address, then each attachment as separate LXMF messages.

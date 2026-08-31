import contextlib

import LXMF
import RNS
import RNS.vendor.umsgpack as msgpack

from meshchatx_issues_bot.config import Settings
from meshchatx_issues_bot.lxmf_hash import normalize_lxmf_hash


def _hash_bytes(value) -> bytes | None:
    h = normalize_lxmf_hash(value)
    if not h:
        return None
    return bytes.fromhex(h)


def recall_identity(address_hash: str) -> RNS.Identity | None:
    raw = _hash_bytes(address_hash)
    if raw is None:
        return None
    identity = RNS.Identity.recall(raw, from_identity_hash=False)
    if identity is None:
        identity = RNS.Identity.recall(raw, from_identity_hash=True)
    return identity


def identity_hash_hex(identity: RNS.Identity) -> str | None:
    raw = getattr(identity, "hash", None)
    if raw is None:
        return None
    if isinstance(raw, bytes):
        return normalize_lxmf_hash(raw.hex())
    return normalize_lxmf_hash(str(raw))


def delivery_hash_hex(identity: RNS.Identity) -> str | None:
    try:
        destination = RNS.Destination(
            identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )
        return normalize_lxmf_hash(destination.hash.hex())
    except Exception:
        return None


def display_name_for_address(address_hash: str, settings: Settings) -> str:
    h = normalize_lxmf_hash(address_hash)
    if not h:
        return "Unknown"

    override = settings.admin_display_names.get(h)
    if override:
        return override

    raw = _hash_bytes(h)
    if raw is None:
        return h

    app_data = RNS.Identity.recall_app_data(raw)
    if app_data:
        with contextlib.suppress(Exception):
            name = LXMF.display_name_from_app_data(app_data)
            if name and str(name).strip() and str(name).strip() != "Anonymous Peer":
                return str(name).strip()

    return h


def _signed_part_from_packed(packed: bytes) -> bytes | None:
    try:
        dest_len = LXMF.LXMessage.DESTINATION_LENGTH
        sig_len = LXMF.LXMessage.SIGNATURE_LENGTH
        if len(packed) < 2 * dest_len + sig_len:
            return None
        destination_hash = packed[:dest_len]
        source_hash = packed[dest_len : 2 * dest_len]
        packed_payload = packed[2 * dest_len + sig_len :]
        unpacked_payload = msgpack.unpackb(packed_payload)
        if len(unpacked_payload) > 4:
            unpacked_payload = unpacked_payload[:4]
            packed_payload = msgpack.packb(unpacked_payload)
        hashed_part = destination_hash + source_hash + packed_payload
        message_hash = RNS.Identity.full_hash(hashed_part)
        return hashed_part + message_hash
    except Exception:
        return None


def _cryptographic_verify(message, identity: RNS.Identity) -> bool:
    signature = getattr(message, "signature", None)
    if not signature:
        return False
    packed = getattr(message, "packed", None)
    if packed:
        signed_part = _signed_part_from_packed(packed)
        if signed_part is not None:
            return bool(identity.validate(signature, signed_part))
    return bool(getattr(message, "signature_validated", False))


def verify_sender(
    message,
    claimed_sender: str,
    settings: Settings,
) -> tuple[bool, str | None, str | None]:
    claimed = normalize_lxmf_hash(claimed_sender)
    if not claimed:
        return False, None, None

    source_raw = getattr(message, "source_hash", None)
    if source_raw is not None:
        if isinstance(source_raw, bytes):
            source_hex = normalize_lxmf_hash(source_raw.hex())
        else:
            source_hex = normalize_lxmf_hash(str(source_raw))
        if source_hex and source_hex != claimed:
            return False, None, None

    identity = recall_identity(claimed)
    if identity is None:
        return False, claimed, None

    id_hash = identity_hash_hex(identity)
    delivery_hash = delivery_hash_hex(identity) or claimed

    if settings.require_identity_verification:
        if not _cryptographic_verify(message, identity):
            return False, delivery_hash, id_hash

    return True, delivery_hash, id_hash


def is_admin_address(
    delivery_hash: str | None,
    identity_hash: str | None,
    settings: Settings,
) -> bool:
    for candidate in (delivery_hash, identity_hash):
        h = normalize_lxmf_hash(candidate) if candidate else None
        if h and h in settings.admin_hashes:
            return True
    return False


def is_verified_admin(ctx, settings: Settings) -> bool:
    claimed = normalize_lxmf_hash(getattr(ctx, "sender", None))
    if not claimed:
        return False

    message = getattr(ctx, "lxmf", None)
    if message is None:
        return is_admin_address(claimed, None, settings)

    ok, delivery_hash, id_hash = verify_sender(message, claimed, settings)
    if not ok:
        return False
    return is_admin_address(delivery_hash, id_hash, settings)

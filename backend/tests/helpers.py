"""Builders for synthetic Claude Code transcript lines."""
import json


def user(uuid, prompt_id, parent, text, ts, session="s1"):
    return {
        "type": "user", "uuid": uuid, "parentUuid": parent, "promptId": prompt_id,
        "sessionId": session, "timestamp": ts, "message": {"role": "user", "content": text},
    }


def attachment(uuid, parent, ts, session="s1"):
    return {"type": "attachment", "uuid": uuid, "parentUuid": parent, "sessionId": session, "timestamp": ts}


def assistant(uuid, parent, ts, model="m", inp=1, out=2, cc=3, cr=4, session="s1",
              message_id=None, request_id=None, cc_1h=None):
    """One transcript entry of a response. Claude Code writes a response as one
    entry per content block, all with the same `message_id`, `request_id` and
    usage; `cc_1h` is how many of the cache writes went to the 1-hour cache."""
    usage = {"input_tokens": inp, "output_tokens": out,
             "cache_creation_input_tokens": cc, "cache_read_input_tokens": cr}
    if cc_1h is not None:
        usage["cache_creation"] = {"ephemeral_5m_input_tokens": cc - cc_1h, "ephemeral_1h_input_tokens": cc_1h}
    entry = {
        "type": "assistant", "uuid": uuid, "parentUuid": parent, "sessionId": session, "timestamp": ts,
        "message": {"model": model, "usage": usage},
    }
    if message_id:
        entry["message"]["id"] = message_id
        entry["requestId"] = request_id or f"req-{message_id}"
    return entry


def write_lines(path, entries, mode="w"):
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, mode, encoding="utf-8") as handle:
        for entry in entries:
            handle.write((entry if isinstance(entry, str) else json.dumps(entry)) + "\n")

"""Call the Anthropic Messages API directly while the runners keep speaking the OpenAI chat format.

A model id like "claude-opus-5-5@anthropic" is sent to https://api.anthropic.com/v1/messages with the key in
ANTHROPIC_API_KEY, adaptive thinking at the effort in ANTHROPIC_EFFORT (default "high"), and prompt caching.
The reply is returned shaped like an OpenAI chat completion. The assistant's raw content blocks (signed thinking
blocks included) are kept in message["anthropic_content"] and sent back verbatim on the next turn, as the API requires.
"""
import json, os, time, urllib.request, urllib.error

URL = "https://api.anthropic.com/v1/messages"
SUFFIX = "@anthropic"
# USD per million tokens: input, output (cache write = 1.25x input, cache read = 0.1x input)
PRICE = {"claude-opus-5-5": (4.0, 20.0)}


def is_native(model):
    return model.endswith(SUFFIX)


def _tools(tools):
    return [{"name": t["function"]["name"], "description": t["function"].get("description", ""),
             "input_schema": t["function"]["parameters"]} for t in tools]


def _messages(messages):
    system, out = "", []
    def push(role, blocks):
        if out and out[-1]["role"] == role: out[-1]["content"].extend(blocks)
        else: out.append({"role": role, "content": list(blocks)})
    for m in messages:
        if m["role"] == "system": system = m["content"]
        elif m["role"] == "user": push("user", [{"type": "text", "text": m["content"]}])
        elif m["role"] == "tool":
            push("user", [{"type": "tool_result", "tool_use_id": m["tool_call_id"], "content": m["content"] or "(no output)"}])
        elif m["role"] == "assistant":
            if m.get("anthropic_content"): push("assistant", m["anthropic_content"])
            else:
                blocks = [{"type": "text", "text": m["content"]}] if m.get("content") else []
                for t in m.get("tool_calls") or []:
                    blocks.append({"type": "tool_use", "id": t["id"], "name": t["function"]["name"],
                                   "input": json.loads(t["function"].get("arguments") or "{}")})
                push("assistant", blocks or [{"type": "text", "text": "(empty)"}])
    # one moving cache breakpoint on the newest block: earlier turns are read back from the cache
    last = out[-1]["content"][-1]
    out[-1]["content"][-1] = {**last, "cache_control": {"type": "ephemeral"}}
    return system, out


def call(model, messages, tools, max_tokens=32768):
    name = model[: -len(SUFFIX)]
    system, msgs = _messages(messages)
    body = {"model": name, "max_tokens": max_tokens, "messages": msgs, "tools": _tools(tools),
            "thinking": {"type": "adaptive"}, "output_config": {"effort": os.environ.get("ANTHROPIC_EFFORT", "high")}}
    if system: body["system"] = [{"type": "text", "text": system, "cache_control": {"type": "ephemeral"}}]
    data = json.dumps(body).encode(); last = None
    for attempt in range(8):
        try:
            req = urllib.request.Request(URL, data=data, headers={"x-api-key": os.environ["ANTHROPIC_API_KEY"],
                                         "anthropic-version": "2023-06-01", "content-type": "application/json"})
            with urllib.request.urlopen(req, timeout=600) as r:
                d = json.loads(r.read().decode())
            break
        except urllib.error.HTTPError as e:
            last = f"HTTP {e.code}: {e.read().decode('utf-8', 'replace')[:300]}"
            if e.code in (400, 401, 403, 404): raise RuntimeError("channel error: " + last)
        except Exception as e:
            last = repr(e)
        time.sleep(min(60, 5 * 2 ** attempt))
    else:
        raise RuntimeError("channel error: " + str(last))
    blocks = d.get("content") or []
    text = "".join(b.get("text", "") for b in blocks if b["type"] == "text")
    thinking = "".join(b.get("thinking", "") for b in blocks if b["type"] == "thinking")
    tcs = [{"id": b["id"], "type": "function", "function": {"name": b["name"], "arguments": json.dumps(b.get("input") or {})}}
           for b in blocks if b["type"] == "tool_use"]
    stop = {"end_turn": "stop", "tool_use": "tool_calls", "max_tokens": "length", "refusal": "content_filter"}.get(d.get("stop_reason"), d.get("stop_reason"))
    u = d.get("usage") or {}
    inp, cw, cr, out = u.get("input_tokens", 0), u.get("cache_creation_input_tokens", 0), u.get("cache_read_input_tokens", 0), u.get("output_tokens", 0)
    pi, po = PRICE.get(name, (0.0, 0.0))
    cost = (inp * pi + cw * pi * 1.25 + cr * pi * 0.1 + out * po) / 1e6
    msg = {"role": "assistant", "content": text, "reasoning": thinking, "anthropic_content": blocks}
    if tcs: msg["tool_calls"] = tcs
    return {"model": d.get("model"), "choices": [{"finish_reason": stop, "message": msg}],
            "usage": {"prompt_tokens": inp + cw + cr, "completion_tokens": out, "cost": cost,
                      "cache_read_tokens": cr, "cache_write_tokens": cw,
                      "completion_tokens_details": {"reasoning_tokens": (u.get("output_tokens_details") or {}).get("thinking_tokens", 0)}}}

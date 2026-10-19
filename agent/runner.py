import json

from .config import DEFAULT_OPTIONS, MAX_STEPS, MODEL_TAG
from .prompts import build_system_prompt
from .tools import DISPATCH, TOOL_SCHEMAS


def run_agent(client, email_id, model=None, variant="baseline", chat_fn=None, options=None, profile=None):
    """Process one email. One email, one run (matches the single-trial threat model).

    chat_fn(model=, messages=, tools=, options=) -> {"message": {...}}. By default this is a
    local Ollama server; the harness injects deterministic mock backends for controls.

    Returns a trace: the list of tool calls made, each with its arguments and result.
    The email is marked processed on the backend at the end, whether or not it was answered.
    """
    if chat_fn is None:
        import ollama

        chat_fn = ollama.chat

    if profile is None:
        profile = client.context()
    messages = [
        {"role": "system", "content": build_system_prompt(profile, variant)},
        {"role": "user", "content": f"Process new email with id {email_id}."},
    ]
    trace = []

    for _ in range(MAX_STEPS):
        resp = chat_fn(
            model=model or MODEL_TAG,
            messages=messages,
            tools=TOOL_SCHEMAS,
            options=options if options is not None else dict(DEFAULT_OPTIONS),
        )
        msg = resp["message"]
        messages.append(msg)
        calls = msg.get("tool_calls") or []
        if not calls:
            break
        for call in calls:
            name = call["function"]["name"]
            args = call["function"]["arguments"]
            if isinstance(args, str):
                args = json.loads(args)
            args = dict(args)
            fn = DISPATCH.get(name)
            try:
                result = fn(client, **args) if fn else f"ERROR: unknown tool {name}"
            except TypeError as e:
                result = f"ERROR: bad arguments ({e})"
            trace.append({"tool": name, "args": args, "result": result})
            messages.append({"role": "tool", "content": result})

    client.mark_processed(email_id)
    return trace

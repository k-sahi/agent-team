"""One function to talk to any model.

Real models go through LiteLLM, which speaks to Anthropic, OpenAI, Google,
Ollama, OpenRouter and ~100 other providers with the same call. Model names
look like "anthropic/claude-sonnet-4-5", "openai/gpt-4o", "ollama/qwen2.5-coder".

Models named "mock/..." are scripted fakes so you can test with no API keys.
"""
import json
import uuid
from dataclasses import dataclass, field


@dataclass
class ToolCall:
    id: str
    name: str
    args: dict


@dataclass
class Reply:
    text: str
    tool_calls: list = field(default_factory=list)
    cost: float = 0.0


def chat(model: str, messages: list, tools: list) -> Reply:
    if model.startswith("mock/"):
        return _mock(model, messages)

    import litellm  # imported here so mock runs don't need it installed

    resp = litellm.completion(model=model, messages=messages, tools=tools)
    msg = resp.choices[0].message
    calls = []
    for tc in msg.tool_calls or []:
        try:
            args = json.loads(tc.function.arguments or "{}")
        except json.JSONDecodeError:
            args = {"_raw": tc.function.arguments}
        calls.append(ToolCall(tc.id, tc.function.name, args))
    if not calls and msg.content:
        # Some local models type the tool call as JSON text instead of making a real call.
        calls = parse_text_tool_calls(msg.content, tools)
    try:
        cost = litellm.completion_cost(completion_response=resp) or 0.0
    except Exception:
        cost = 0.0  # local models / unknown pricing
    return Reply(msg.content or "", calls, cost)


def parse_text_tool_calls(text: str, tools: list) -> list:
    """Find tool calls written as JSON text, like {"name": "read_file", "arguments": {...}}.

    Only names of tools the agent actually has are accepted, so ordinary JSON in a
    reply is ignored.
    """
    names = {t["function"]["name"] for t in tools}
    decoder = json.JSONDecoder()
    calls, i = [], 0
    while (i := text.find("{", i)) != -1:
        try:
            obj, end = decoder.raw_decode(text, i)
        except json.JSONDecodeError:
            i += 1
            continue
        if isinstance(obj, dict) and obj.get("name") in names:
            args = obj.get("arguments", obj.get("parameters", {}))
            if isinstance(args, str):
                try:
                    args = json.loads(args)
                except json.JSONDecodeError:
                    args = None
            if isinstance(args, dict):
                calls.append(ToolCall(f"call_{uuid.uuid4().hex[:8]}", obj["name"], args))
            i = end
        else:
            i += 1
    return calls


# ---------------------------------------------------------------- mock models

_MOCK_SCRIPTS = {
    "builder": [
        ("write_file", {"path": "hello.py",
                        "content": 'def greet(name):\n    return f"Hello, {name}!"\n\n'
                                   'if __name__ == "__main__":\n    print(greet("world"))\n'}),
        ("finish", {"summary": "Wrote hello.py with a greet() function."}),
    ],
    "reviewer": [
        ("read_file", {"path": "hello.py"}),
        ("run_command", {"command": "python hello.py"}),
        ("finish", {"verdict": "approve", "feedback": "Runs and prints the greeting."}),
    ],
}


def _mock(model: str, messages: list) -> Reply:
    role = model.split("/", 1)[1]
    script = _MOCK_SCRIPTS.get(role, _MOCK_SCRIPTS["builder"])
    # Step = assistant turns since the last user message (restarts each round).
    step = 0
    for m in reversed(messages):
        if m["role"] == "user":
            break
        if m["role"] == "assistant":
            step += 1
    name, args = script[min(step, len(script) - 1)]
    return Reply(f"(mock {role} step {step})", [ToolCall(f"call_{step}", name, args)])
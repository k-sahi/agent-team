"""The agent loop: ask the model, run the tool it picks, feed the result back, repeat."""
import json

from models import chat
from tools import FINISH_SCHEMAS, TOOL_SCHEMAS


class Agent:
    def __init__(self, name, kind, model, prompt, tools, workspace, emit, max_steps=30):
        self.name = name
        self.kind = kind            # "builder" or "reviewer" (decides the finish tool)
        self.model = model
        self.workspace = workspace
        self.emit = emit            # callable(agent_name, event_type, text) -> for the UI
        self.max_steps = max_steps
        self.cost = 0.0
        self.tools = [TOOL_SCHEMAS[t] for t in tools] + [FINISH_SCHEMAS[kind]]
        self.messages = [{"role": "system", "content": prompt}]

    def run(self, instruction: str) -> dict:
        """Work on `instruction` until the model calls finish. Returns finish's arguments.
        History is kept, so calling run() again continues the same conversation."""
        self.messages.append({"role": "user", "content": instruction})
        self.emit(self.name, "start", instruction.splitlines()[0][:120])

        for _ in range(self.max_steps):
            try:
                reply = chat(self.model, self.messages, self.tools)
            except Exception as e:
                self.emit(self.name, "error", f"model call failed: {e}")
                return {"error": str(e)}
            self.cost += reply.cost

            if reply.text.strip():
                self.emit(self.name, "think", reply.text.strip())

            if not reply.tool_calls:
                # Model answered in plain text; nudge it to use tools or finish.
                self.messages.append({"role": "assistant", "content": reply.text})
                self.messages.append({"role": "user", "content":
                                      "Continue using the tools. Call finish when you are done."})
                continue

            self.messages.append({
                "role": "assistant", "content": reply.text or None,
                "tool_calls": [{"id": c.id, "type": "function",
                                "function": {"name": c.name, "arguments": json.dumps(c.args)}}
                               for c in reply.tool_calls]})

            finished = None
            for call in reply.tool_calls:
                if call.name == "finish":
                    finished = call.args
                    result = "finished"  # every tool call needs a reply to keep history valid
                else:
                    self.emit(self.name, "tool", _describe(call.name, call.args))
                    result = self.workspace.call(self.name, call.name, call.args)
                    self.emit(self.name, "result", result)
                self.messages.append({"role": "tool", "tool_call_id": call.id, "content": result})
            if finished is not None:
                self.emit(self.name, "finish", json.dumps(finished))
                return finished

        self.emit(self.name, "error", f"hit the {self.max_steps}-step limit")
        return {"error": "step limit"}


def _describe(name, args):
    if name == "write_file":
        return f"write_file {args.get('path')} ({len(args.get('content', ''))} chars)"
    if name == "run_command":
        return f"$ {args.get('command')}"
    return f"{name} {args.get('path', '')}".strip()
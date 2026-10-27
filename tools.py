"""Tools the agents can use. Every path is confined to the project folder."""
import subprocess
from pathlib import Path

MAX_OUTPUT = 8000  # characters of tool output sent back to the model


class Workspace:
    def __init__(self, root, approve_command=None, command_timeout=60):
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)
        self.approve_command = approve_command  # callable(agent, cmd) -> bool, or None
        self.command_timeout = command_timeout

    def _path(self, rel):
        p = (self.root / rel).resolve()
        if p != self.root and self.root not in p.parents:
            raise ValueError(f"path escapes the project folder: {rel}")
        return p

    # --- the tools -----------------------------------------------------------

    def list_files(self, agent, path="."):
        base = self._path(path)
        skip = {".git", "__pycache__", "node_modules", ".venv"}
        out = []
        for p in sorted(base.rglob("*")):
            if any(part in skip for part in p.relative_to(self.root).parts):
                continue
            if p.is_file():
                out.append(p.relative_to(self.root).as_posix())
        return "\n".join(out) or "(empty)"

    def read_file(self, agent, path):
        return self._path(path).read_text(encoding="utf-8", errors="replace")

    def write_file(self, agent, path, content):
        p = self._path(path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return f"wrote {path} ({len(content)} chars)"

    def run_command(self, agent, command):
        if self.approve_command and not self.approve_command(agent, command):
            return "command was declined by the user"
        try:
            r = subprocess.run(command, shell=True, cwd=self.root, capture_output=True,
                               text=True, timeout=self.command_timeout)
        except subprocess.TimeoutExpired:
            return f"timed out after {self.command_timeout}s"
        return f"exit code {r.returncode}\n{r.stdout}{r.stderr}"

    def call(self, agent, name, args):
        fn = getattr(self, name, None)
        if name not in TOOL_SCHEMAS or fn is None:
            return f"unknown tool: {name}"
        try:
            result = str(fn(agent, **args))
        except Exception as e:
            result = f"error: {type(e).__name__}: {e}"
        if len(result) > MAX_OUTPUT:
            result = result[:MAX_OUTPUT] + f"\n... (truncated, {len(result)} chars total)"
        return result


def _schema(name, desc, props, required):
    return {"type": "function", "function": {
        "name": name, "description": desc,
        "parameters": {"type": "object", "properties": props, "required": required}}}


_S = {"type": "string"}

TOOL_SCHEMAS = {
    "list_files": _schema("list_files", "List files in the project (recursive).",
                          {"path": {**_S, "description": "folder, default '.'"}}, []),
    "read_file": _schema("read_file", "Read a text file.", {"path": _S}, ["path"]),
    "write_file": _schema("write_file", "Create or overwrite a file with the full content.",
                          {"path": _S, "content": _S}, ["path", "content"]),
    "run_command": _schema("run_command", "Run a shell command in the project folder "
                           "(tests, scripts, installs). Returns exit code and output.",
                           {"command": _S}, ["command"]),
}

# 'finish' is handled by the agent loop, not the workspace. Its arguments differ per role.
FINISH_SCHEMAS = {
    "builder": _schema("finish", "Call when the task is done.",
                       {"summary": {**_S, "description": "what you built/changed"}}, ["summary"]),
    "reviewer": _schema("finish", "Call with your verdict when the review is done.",
                        {"verdict": {"type": "string", "enum": ["approve", "changes"]},
                         "feedback": {**_S, "description": "specific problems to fix, or why it passes"}},
                        ["verdict", "feedback"]),
}
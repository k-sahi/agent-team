"""Live terminal view: one panel per agent plus a status line."""
from collections import deque

# Rich is imported inside LiveUI so --plain mode works without it installed.

STYLES = {"start": "bold cyan", "think": "italic", "tool": "yellow", "result": "dim",
          "finish": "bold green", "error": "bold red", "round": "bold magenta",
          "done": "bold green"}


class LiveUI:
    def __init__(self, team_ref, member_names, lines=40):
        self.team_ref = team_ref          # callable returning the Team (for cost)
        self.names = list(member_names)
        self.events = {n: deque(maxlen=lines) for n in self.names}
        self.status = "starting"
        self.active = None
        from rich.live import Live
        self.live = Live(self._render(), refresh_per_second=8, screen=False)

    def emit(self, agent, kind, text):
        if agent == "team":
            self.status = text
        else:
            self.active = agent
            for line in _shorten(kind, text):
                self.events[agent].append((kind, line))
        self.live.update(self._render())

    def approve(self, agent, command):
        self.live.stop()
        ans = input(f"\n{agent} wants to run:  {command}\nAllow? [y/N] ").strip().lower()
        self.live.start()
        return ans in ("y", "yes")

    def _render(self):
        from rich.layout import Layout
        from rich.text import Text
        row = Layout()
        row.split_row(*[Layout(self._panel(n)) for n in self.names])
        team = self.team_ref()
        cost = f"${team.cost:.4f}" if team else "$0"
        status = Text(f" {self.status}   |   spend {cost} ", style="reverse")
        root = Layout()
        root.split_column(Layout(row, ratio=1), Layout(status, size=1))
        return root

    def _panel(self, name):
        from rich.panel import Panel
        from rich.text import Text
        body = Text()
        for kind, line in self.events[name]:
            body.append(line + "\n", style=STYLES.get(kind, ""))
        team = self.team_ref()
        model = team.agents[name].model if team else ""
        border = "green" if name == self.active else "grey50"
        return Panel(body, title=f"{name}  [dim]{model}[/dim]", border_style=border)


def _shorten(kind, text):
    lines = text.splitlines() or [""]
    limit = 6 if kind == "result" else 4
    out = lines[:limit]
    if len(lines) > limit:
        out.append(f"... (+{len(lines) - limit} lines)")
    prefix = {"tool": "→ ", "result": "  ", "finish": "✓ ", "error": "✗ "}.get(kind, "")
    return [prefix + l[:200] for l in out]


class PlainUI:
    """Line-by-line output, for logs, CI, or terminals without full-screen support."""

    def __init__(self, approve_commands=False):
        self.approve_commands = approve_commands

    def emit(self, agent, kind, text):
        for line in _shorten(kind, text):
            print(f"[{agent}:{kind}] {line}", flush=True)

    def approve(self, agent, command):
        return input(f"{agent} wants to run: {command}  Allow? [y/N] ").strip().lower() in ("y", "yes")
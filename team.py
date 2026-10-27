"""Runs the team: builder works, reviewer checks, repeat until approved."""
import tomllib

from agent import Agent
from tools import Workspace


def load_config(path):
    with open(path, "rb") as f:
        return tomllib.load(f)


class Team:
    def __init__(self, config, project_dir, emit, approve_command=None):
        self.config = config
        self.emit = emit
        settings = config.get("settings", {})
        self.max_rounds = settings.get("max_rounds", 3)
        self.budget = settings.get("budget_usd", 2.0)
        self.workspace = Workspace(project_dir, approve_command,
                                   settings.get("command_timeout", 60))

        self.agents = {}
        for name, m in config["members"].items():
            self.agents[name] = Agent(
                name=name, kind=m["kind"], model=m["model"], prompt=m["prompt"].strip(),
                tools=m.get("tools", ["list_files", "read_file", "write_file", "run_command"]),
                workspace=self.workspace, emit=emit, max_steps=settings.get("max_steps", 30))
        kinds = [a.kind for a in self.agents.values()]
        if kinds.count("builder") != 1 or kinds.count("reviewer") != 1:
            raise ValueError("this version needs exactly one builder and one reviewer")
        self.builder = next(a for a in self.agents.values() if a.kind == "builder")
        self.reviewer = next(a for a in self.agents.values() if a.kind == "reviewer")

    @property
    def cost(self):
        return sum(a.cost for a in self.agents.values())

    def run(self, task):
        instruction = f"Task:\n{task}"
        for rnd in range(1, self.max_rounds + 1):
            self.emit("team", "round", f"round {rnd} of {self.max_rounds}")

            built = self.builder.run(instruction)
            if "error" in built:
                return self._end(False, f"builder stopped: {built['error']}")
            if self.cost > self.budget:
                return self._end(False, f"budget of ${self.budget:.2f} reached")

            review = self.reviewer.run(
                f"Original task:\n{task}\n\nThe builder says:\n{built.get('summary', '')}\n\n"
                "Review the code in the project folder. Read the files and run them or their "
                "tests. Approve only if the task is fully and correctly done.")
            if "error" in review:
                return self._end(False, f"reviewer stopped: {review['error']}")
            if review.get("verdict") == "approve":
                return self._end(True, f"approved: {review.get('feedback', '')}")
            if self.cost > self.budget:
                return self._end(False, f"budget of ${self.budget:.2f} reached")

            instruction = ("The reviewer asked for changes:\n" + review.get("feedback", "") +
                           "\n\nFix these, then call finish.")
        return self._end(False, f"not approved after {self.max_rounds} rounds")

    def _end(self, ok, message):
        self.emit("team", "done" if ok else "error", f"{message}  (cost ${self.cost:.4f})")
        return ok
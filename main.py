"""agent-team: a builder and a reviewer, on different models, working on one project.

    python main.py "build a CLI todo app with tests" --dir ./my-project
    python main.py "..." --config team.mock.toml --plain   # offline test, no keys
"""
import argparse
import sys

from team import Team, load_config


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("task", help="what you want built or changed")
    ap.add_argument("--dir", default="./workspace", help="project folder the agents work in")
    ap.add_argument("--config", default="team.toml", help="team definition file")
    ap.add_argument("--plain", action="store_true", help="plain line output instead of live panels")
    ap.add_argument("--yolo", action="store_true", help="run shell commands without asking")
    args = ap.parse_args()

    # Windows terminals may not default to UTF-8; this keeps symbols like → and ✓ from crashing.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    config = load_config(args.config)
    ask = config.get("settings", {}).get("approve_commands", True) and not args.yolo

    holder = {"team": None}
    if args.plain:
        from ui import PlainUI
        ui = PlainUI()
    else:
        from ui import LiveUI
        ui = LiveUI(lambda: holder["team"], config["members"].keys())

    team = Team(config, args.dir, ui.emit, ui.approve if ask else None)
    holder["team"] = team

    if args.plain:
        ok = team.run(args.task)
    else:
        with ui.live:
            ok = team.run(args.task)
    print(f"\nDone. Total spend ${team.cost:.4f}. Files are in {team.workspace.root}")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
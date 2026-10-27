# agent-team

**A team of AI coding agents, on any mix of models, working on one project, live in your terminal.**

A **builder** agent writes and runs code. A **reviewer** agent, on a different model, reads it, runs it, and either approves it or sends back specific fixes. They go back and forth until the work is approved, the round limit is reached, or the budget runs out.

```
task ──► BUILDER (e.g. Claude) ──summary──► REVIEWER (e.g. GPT) ──► approved ✓
               ▲                                  │
               └────────── "changes: fix X" ◄─────┘
```

## Features
- **Any model, mixed freely:** Claude, GPT, Gemini, local Ollama models and more, via LiteLLM
- **Live terminal view:** side-by-side panels for each agent, plus round and spending status
- **Safe by default:** file access is limited to one project folder, every shell command needs approval, and the reviewer is read-only
- **Cost control:** budget, round and step limits
- **Free offline testing:** scripted mock models and 28 unit tests

## Quick start (Windows PowerShell)
```powershell
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt

# free test with fake models
python main.py "write a hello world script" --config team.mock.toml

# real run
$env:ANTHROPIC_API_KEY="..."
$env:OPENAI_API_KEY="..."
python main.py "build a command-line todo app with tests" --dir .\todo
```

## How it's built
| File | Role |
|---|---|
| `models.py` | One `chat()` call for any model, plus mock models |
| `tools.py` | File and shell tools, limited to the project folder |
| `agent.py` | The agent loop: model picks a tool → tool runs → result goes back |
| `team.py` | Builder → reviewer rounds with budget and round limits |
| `ui.py` / `main.py` | Live terminal panels and the command-line entry point |

## Run the tests
```powershell
python -m unittest -v
```
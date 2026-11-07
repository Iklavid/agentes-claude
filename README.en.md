# Claude Code agents on a Mac (with a front desk)

[Español](README.md)

How to keep several [Claude Code](https://claude.com/claude-code) agents always running on a home computer, each with its own area. A **front-desk** agent ("Recepción") takes your requests and hands each one to the right agent. You talk to them from your phone through Remote Control (Claude app) or a Telegram bot. The templates and the code are in Spanish.

- `bin/claude-agente.sh` starts each agent in its own tmux session.
- A launchd plist restarts any agent that has stopped, every 5 minutes.
- `plantillas/` holds the shared rules (`CLAUDE.md`), the front-desk role and a shared task list (`pendientes.md`).
- `hooks/guardia.py` is a `PreToolUse` hook that blocks reading secret files and closing the agents' sessions.
- `mejora/mejora.py` runs every week: it finds repeated corrections and repeated requests (skill candidates) and sends a summary by Telegram.
- `panel/` is a web page showing each agent's state (free, busy or stopped), tokens and tasks.

The Spanish README has the step-by-step setup.

## License
**Free for personal and other noncommercial use** under the [PolyForm Noncommercial License 1.0.0](LICENSE.md). Commercial use needs a paid commercial license: contact me on [GitHub](https://github.com/Iklavid).
Because it restricts commercial use, this license is not "open source" under the OSI definition; the source code is still public.
`mejora/mejora.py` adapts *improve-system* from [charlie947/skills-for-everyone](https://github.com/charlie947/skills-for-everyone) and keeps its MIT license (`mejora/LICENSE-MIT`).

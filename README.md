# agentwatch

Behavioral monitor for local AI agents. Logs every tool call an agent makes,
scores it against a rule set, and blocks the dangerous ones. Think of it as a
tiny EDR for your Ollama agent.

**Rogue = acts outside its mandate.** You can't read an agent's mind, but you
can audit every action it takes. Detections map to real attacker behavior:

| Rule | MITRE ATT&CK | What it catches |
|---|---|---|
| path_escape / secret_access | T1552 Unsecured Credentials | reading `.env`, `~/.ssh`, `/etc/` |
| destructive_shell | T1485 Data Destruction | `rm -rf`, `mkfs`, fork bombs |
| privilege_esc | T1548 Abuse Elevation | `sudo`, `su`, `passwd` |
| outbound_net / exfil_url | T1041 Exfiltration over C2 | `curl`, `wget`, webhooks, pastebin |
| persistence | T1053 Scheduled Task | `crontab`, `systemctl`, `.bashrc` |
| self_modify | T1562 Impair Defenses | editing `monitor.py` / `rules.json` |
| rate_limit_exceeded | — | runaway loops / resource seeking |

## Usage
```bash
python3 demo_agent.py          # watch a fake agent go rogue and get blocked
python3 monitor.py report      # summarize the latest session log
```
Wrap your own agent's tools:
```python
from monitor import watch
@watch
def shell(cmd): ...
```
Logs land in `logs/session_*.jsonl` — one JSON line per call, ready for Splunk.

## Limits (honest version)
Regex rules only. Obfuscated commands (`base64 -d | sh`) slip past. Next steps:
AST parsing of shell commands, network egress via firewall rules not regex,
and running the agent inside Docker with `--network none` as the real control.

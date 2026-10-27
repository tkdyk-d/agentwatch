"""agentwatch — behavioral monitor for local AI agents.

Wrap any tool function with @watch; every call is logged, scored against
rules.json, and BLOCKED if it hits a critical rule. Run `python monitor.py report`
to summarize a session log.
"""
import json, re, time, functools, sys, pathlib
from datetime import datetime, timezone

RULES = json.loads(pathlib.Path(__file__).with_name("rules.json").read_text())
LOG = pathlib.Path("logs"); LOG.mkdir(exist_ok=True)
SESSION = LOG / f"session_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jsonl"

class RogueActionBlocked(Exception): pass

def _score(tool, args):
    """Return (score, [rule names]) for one tool call."""
    text = f"{tool} {json.dumps(args, default=str)}"
    hits, score = [], 0
    for r in RULES["rules"]:
        if r["tool"] not in ("*", tool): continue
        if re.search(r["pattern"], text, re.I):
            hits.append(r["name"]); score += r["severity"]
    return score, hits

_counts = {}
def watch(fn):
    """Decorator: audit + enforce policy on a tool function."""
    @functools.wraps(fn)
    def wrapper(*a, **kw):
        tool = fn.__name__
        args = {"args": a, "kwargs": kw}
        score, hits = _score(tool, args)
        _counts[tool] = _counts.get(tool, 0) + 1
        if _counts[tool] > RULES["max_calls_per_tool"]:
            score += 5; hits.append("rate_limit_exceeded")   # resource-seeking loop
        verdict = "BLOCK" if score >= RULES["block_threshold"] else \
                  "FLAG"  if score >= RULES["flag_threshold"]  else "OK"
        rec = {"ts": datetime.now(timezone.utc).isoformat(), "tool": tool,
               "args": args, "score": score, "rules": hits, "verdict": verdict}
        try:
            if verdict == "BLOCK":
                raise RogueActionBlocked(f"{tool} blocked: {hits}")
            out = fn(*a, **kw)
            rec["result"] = str(out)[:300]
            return out
        except RogueActionBlocked:
            rec["result"] = "BLOCKED"; raise
        finally:
            with SESSION.open("a") as f: f.write(json.dumps(rec, default=str) + "\n")
            print(f"[agentwatch] {verdict:5} {tool} score={score} {hits}")
    return wrapper

def report(path=None):
    """Summarize a session log: what the agent did, and what it tried to do."""
    p = pathlib.Path(path) if path else max(LOG.glob("session_*.jsonl"))
    recs = [json.loads(l) for l in p.read_text().splitlines()]
    by = {"OK":0,"FLAG":0,"BLOCK":0}
    for r in recs: by[r["verdict"]] += 1
    print(f"\n== {p.name} == calls={len(recs)} {by}")
    for r in recs:
        if r["verdict"] != "OK":
            print(f"  {r['verdict']:5} {r['tool']:12} {r['rules']}  {str(r['args'])[:80]}")
    risk = "ROGUE" if by["BLOCK"] else "SUSPICIOUS" if by["FLAG"] else "CLEAN"
    print(f"VERDICT: {risk}\n")

if __name__ == "__main__" and len(sys.argv) > 1 and sys.argv[1] == "report":
    report(sys.argv[2] if len(sys.argv) > 2 else None)

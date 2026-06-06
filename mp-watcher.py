"""
mp-watcher.py — Clipboard watcher for MemoryPlugin + Understand-Anything.

TWO PROTOCOLS run in parallel:

  [mp] blocks  — MemoryPlugin API calls
  [ua] blocks  — Understand-Anything knowledge graph queries (local JSON)

Copy any message containing one or both block types. The watcher fires
after a 2-second cancellable delay and puts results back on the clipboard.

────────────────────────────────────────────────────────────────────────
MEMORY PLUGIN COMMANDS (action field):
  search      {"action": "search",      "query": "..."}
  get         {"action": "get",         "latest": true, "count": 10}
  get all     {"action": "get",         "all": true}
  store       {"action": "store",       "text": "..."}
  buckets     {"action": "get_buckets"}
  chat recall {"action": "recall_chat", "query": "..."}

UNDERSTAND-ANYTHING COMMANDS (action field):
  ua_info     {"action": "ua_info",   "path": "optional/path"}
              → Project summary: name, languages, node/edge counts, layers
  ua_search   {"action": "ua_search", "query": "auth", "path": "optional/path", "count": 10}
              → Fuzzy search nodes by name, summary, tags, filePath
  ua_node     {"action": "ua_node",   "id": "file:src/auth.ts", "path": "optional/path"}
              → Full detail on a specific node plus its direct edges
  ua_layer    {"action": "ua_layer",  "name": "API", "path": "optional/path"}
              → All nodes in a named architectural layer
  ua_tour     {"action": "ua_tour",   "path": "optional/path"}
              → The guided learning tour steps

  "path" is optional in all ua commands. If omitted the watcher searches
  common locations (current dir, genesis-pantheon, C:\\m, Desktop).
────────────────────────────────────────────────────────────────────────

SETUP:
  pip install pyperclip requests --break-system-packages
  Set MEMORY_PLUGIN_TOKEN below, then:
  python C:\\m\\mp-watcher.py
"""

import json
import os
import re
import sys
import time
import datetime

import pyperclip
import requests

# ── CONFIG ────────────────────────────────────────────────────────────────────
MEMORY_PLUGIN_TOKEN = os.environ.get("MEMORY_PLUGIN_TOKEN", "")
POLL_INTERVAL       = 0.5    # seconds between clipboard checks
FIRE_DELAY          = 2.0    # seconds to wait before firing
BASE_URL            = "https://www.memoryplugin.com"
SOURCE              = "deepseek-watcher"

# Directories to search for knowledge-graph.json when no path given
UA_SEARCH_DIRS = [
    os.getcwd(),
    r"C:\Users\cccom\genesis-pantheon",
    r"C:\m",
    os.path.join(os.path.expanduser("~"), "Desktop"),
]
# ─────────────────────────────────────────────────────────────────────────────

HEADERS = {
    "Authorization": f"Bearer {MEMORY_PLUGIN_TOKEN}",
    "Content-Type":  "application/json",
}

# Regexes — built without writing literal trigger strings inline
_MP_TAG = "mp"
_UA_TAG = "ua"
MP_RE = re.compile(r"```" + _MP_TAG + r"\s*([\s\S]*?)```", re.IGNORECASE)
UA_RE = re.compile(r"```" + _UA_TAG + r"\s*([\s\S]*?)```", re.IGNORECASE)


def today_utc():
    return datetime.datetime.utcnow().strftime("%Y-%m-%d")


# ════════════════════════════════════════════════════════════════════════════
# MEMORY PLUGIN — API calls
# ════════════════════════════════════════════════════════════════════════════

def api_search(query, count=10, bucket_id=None):
    params = {"query": query, "count": count, "source": SOURCE, "v": 2}
    if bucket_id:
        params["bucketId"] = bucket_id
    r = requests.get(f"{BASE_URL}/api/v2/memory", headers=HEADERS,
                     params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def api_get(all_=False, latest=False, count=10, bucket_id=None):
    params = {"source": SOURCE, "v": 2, "count": count}
    if all_:    params["all"] = "true"
    if latest:  params["latest"] = "true"
    if bucket_id: params["bucketId"] = bucket_id
    r = requests.get(f"{BASE_URL}/api/v2/memory", headers=HEADERS,
                     params=params, timeout=15)
    r.raise_for_status()
    return r.json()


def api_store(text, bucket_id=None):
    dated = f"{today_utc()} {text}"
    body  = {"text": dated, "source": SOURCE}
    if bucket_id: body["bucketId"] = bucket_id
    r = requests.post(f"{BASE_URL}/api/memory", headers=HEADERS,
                      json=body, timeout=15)
    r.raise_for_status()
    return r.json()


def api_get_buckets():
    r = requests.get(f"{BASE_URL}/api/buckets", headers=HEADERS, timeout=15)
    r.raise_for_status()
    return r.json()


def api_recall_chat(query):
    body = {"query": query, "source": SOURCE}
    r = requests.post(f"{BASE_URL}/api/chat-history/recall", headers=HEADERS,
                      json=body, timeout=30)
    r.raise_for_status()
    return r.json()


def _unpack(result):
    if isinstance(result, list):
        return result, []
    memories = result.get("memories") or result.get("data") or []
    buckets  = result.get("buckets") or []
    return memories, buckets


def _fmt_memories(memories, buckets, header):
    lines = [header]
    if not memories:
        lines.append("  (none)")
    else:
        for i, m in enumerate(memories, 1):
            text = m.get("text") if isinstance(m, dict) else m
            lines.append(f"  {i}. {text}")
    if buckets:
        lines.append("")
        lines.append("[BUCKETS] " + ", ".join(
            f"{b.get('name','?')} (id={b.get('id','?')})" for b in buckets))
    return "\n".join(lines)


def dispatch_mp(cmd):
    action    = cmd.get("action", "").lower().strip()
    bucket_id = cmd.get("bucketId") or cmd.get("bucket_id")

    if action == "search":
        result            = api_search(cmd["query"], cmd.get("count", 10), bucket_id)
        memories, buckets = _unpack(result)
        return _fmt_memories(memories, buckets, "[MP SEARCH RESULTS]")

    elif action == "get":
        result            = api_get(cmd.get("all", False), cmd.get("latest", False),
                                    cmd.get("count", 10), bucket_id)
        memories, buckets = _unpack(result)
        return _fmt_memories(memories, buckets, "[MP MEMORIES]")

    elif action == "store":
        text = cmd.get("text") or cmd.get("content") or cmd.get("memory")
        if not text:
            return "[MP ERROR] store requires a 'text' field"
        api_store(text, bucket_id)
        return f'[MP STORED] OK: "{text}"'

    elif action == "get_buckets":
        result  = api_get_buckets()
        buckets = result if isinstance(result, list) else result.get("data", [])
        if not buckets:
            return "[MP BUCKETS] (none)"
        lines = ["[MP BUCKETS]"]
        for b in buckets:
            lines.append(f"  id={b.get('id')}  name={b.get('name')}  "
                         f"count={b.get('memoryCount', '?')}  "
                         f"{b.get('description', '')}")
        return "\n".join(lines)

    elif action in ("recall_chat", "recall"):
        result  = api_recall_chat(cmd["query"])
        summary = (result.get("summary") or result.get("data")
                   or json.dumps(result, indent=2))
        return f"[MP CHAT RECALL]\n{summary}"

    else:
        return (f"[MP ERROR] Unknown action: {action!r}\n"
                f"  Valid: search | get | store | get_buckets | recall_chat")


# ════════════════════════════════════════════════════════════════════════════
# UNDERSTAND-ANYTHING — local knowledge graph queries
# ════════════════════════════════════════════════════════════════════════════

def _ua_find_graph(path_hint=None):
    """Locate knowledge-graph.json. path_hint may be a dir or full file path."""
    candidates = []

    if path_hint:
        p = os.path.expanduser(path_hint)
        if os.path.isfile(p):
            candidates.append(p)
        else:
            candidates.append(os.path.join(p, ".understand-anything", "knowledge-graph.json"))

    for d in UA_SEARCH_DIRS:
        candidates.append(os.path.join(d, ".understand-anything", "knowledge-graph.json"))

    for c in candidates:
        if os.path.isfile(c):
            return c
    return None


def _ua_load(path_hint=None):
    """Load and return (graph_dict, graph_path) or raise."""
    p = _ua_find_graph(path_hint)
    if not p:
        raise FileNotFoundError(
            "No knowledge-graph.json found. Run /understand in Gemini CLI, "
            "OpenCode, or Hermes first to generate one.")
    with open(p, encoding="utf-8") as f:
        return json.load(f), p


def _ua_score(node, query):
    """Simple relevance score: count query word hits across key fields."""
    q_words = query.lower().split()
    text = " ".join([
        node.get("name", ""),
        node.get("summary", ""),
        node.get("filePath", ""),
        node.get("id", ""),
        " ".join(node.get("tags", [])),
    ]).lower()
    return sum(1 for w in q_words if w in text)


def dispatch_ua(cmd):
    action     = cmd.get("action", "").lower().strip()
    path_hint  = cmd.get("path")
    count      = int(cmd.get("count", 10))

    try:
        graph, graph_path = _ua_load(path_hint)
    except FileNotFoundError as e:
        return f"[UA ERROR] {e}"
    except Exception as e:
        return f"[UA ERROR] Failed to load graph: {e}"

    proj    = graph.get("project", {})
    nodes   = graph.get("nodes", [])
    edges   = graph.get("edges", [])
    layers  = graph.get("layers", [])
    tour    = graph.get("tour", [])
    src     = os.path.relpath(graph_path) if len(graph_path) < 60 else graph_path

    # ── ua_info ──────────────────────────────────────────────────────────
    if action == "ua_info":
        type_counts = {}
        for n in nodes:
            t = n.get("type", "?")
            type_counts[t] = type_counts.get(t, 0) + 1
        edge_counts = {}
        for e in edges:
            t = e.get("type", "?")
            edge_counts[t] = edge_counts.get(t, 0) + 1

        lines = [
            f"[UA INFO] {graph_path}",
            f"  Project : {proj.get('name', '?')}",
            f"  Desc    : {proj.get('description', '(none)')[:120]}",
            f"  Langs   : {', '.join(proj.get('languages', []))}",
            f"  Analyzed: {proj.get('analyzedAt', '?')}",
            f"  Nodes   : {len(nodes)}  Edges: {len(edges)}  "
            f"Layers: {len(layers)}  Tour steps: {len(tour)}",
            "",
            "  Node types:",
        ]
        for t, c in sorted(type_counts.items(), key=lambda x: -x[1]):
            lines.append(f"    {t}: {c}")
        lines.append("  Edge types:")
        for t, c in sorted(edge_counts.items(), key=lambda x: -x[1])[:8]:
            lines.append(f"    {t}: {c}")
        lines.append("  Layers: " + ", ".join(l.get("name", "?") for l in layers))
        return "\n".join(lines)

    # ── ua_search ─────────────────────────────────────────────────────────
    elif action == "ua_search":
        query = cmd.get("query", "").strip()
        if not query:
            return "[UA ERROR] ua_search requires a 'query' field"

        scored = [(n, _ua_score(n, query)) for n in nodes]
        scored = [(n, s) for n, s in scored if s > 0]
        scored.sort(key=lambda x: -x[1])
        top = scored[:count]

        if not top:
            return f"[UA SEARCH] No nodes matched '{query}' in {src}"

        lines = [f"[UA SEARCH] '{query}' — {len(scored)} matches, showing top {len(top)}"]
        for n, score in top:
            fp = n.get("filePath", "")
            summary = n.get("summary", "")[:80]
            tags = ", ".join(n.get("tags", [])[:4])
            lines.append(f"\n  [{n.get('type','?')}] {n.get('name','?')}")
            lines.append(f"    id     : {n.get('id','?')}")
            if fp: lines.append(f"    file   : {fp}")
            if summary: lines.append(f"    summary: {summary}")
            if tags: lines.append(f"    tags   : {tags}")
        return "\n".join(lines)

    # ── ua_node ───────────────────────────────────────────────────────────
    elif action == "ua_node":
        node_id = cmd.get("id", "").strip()
        if not node_id:
            return "[UA ERROR] ua_node requires an 'id' field"

        node = next((n for n in nodes if n.get("id") == node_id), None)
        if not node:
            # try partial match
            node = next((n for n in nodes if node_id.lower() in n.get("id","").lower()), None)
        if not node:
            return f"[UA ERROR] Node '{node_id}' not found"

        nid = node["id"]
        out_edges = [e for e in edges if e.get("source") == nid]
        in_edges  = [e for e in edges if e.get("target") == nid]

        lines = [
            f"[UA NODE] {node.get('name','?')}",
            f"  id      : {nid}",
            f"  type    : {node.get('type','?')}",
            f"  file    : {node.get('filePath','')}",
            f"  tags    : {', '.join(node.get('tags',[]))}",
            f"  complex : {node.get('complexity','')}",
            f"  summary : {node.get('summary','')}",
        ]
        if node.get("languageNotes"):
            lines.append(f"  notes   : {node['languageNotes'][:120]}")

        if out_edges:
            lines.append(f"\n  → Outgoing ({len(out_edges)}):")
            for e in out_edges[:8]:
                lines.append(f"    {e.get('type','?')} → {e.get('target','?')}")

        if in_edges:
            lines.append(f"\n  ← Incoming ({len(in_edges)}):")
            for e in in_edges[:8]:
                lines.append(f"    {e.get('source','?')} → {e.get('type','?')}")

        return "\n".join(lines)

    # ── ua_layer ──────────────────────────────────────────────────────────
    elif action == "ua_layer":
        name_q = cmd.get("name", "").lower().strip()
        layer  = next((l for l in layers
                       if name_q in l.get("name","").lower()), None)
        if not layer:
            avail = ", ".join(l.get("name","?") for l in layers)
            return f"[UA ERROR] Layer '{name_q}' not found. Available: {avail}"

        node_ids = layer.get("nodeIds", [])
        node_map = {n["id"]: n for n in nodes}
        lines = [
            f"[UA LAYER] {layer.get('name','?')}",
            f"  {layer.get('description','')}",
            f"  {len(node_ids)} nodes:",
        ]
        for nid in node_ids[:count]:
            n = node_map.get(nid, {})
            lines.append(f"  • [{n.get('type','?')}] {n.get('name', nid)}"
                         + (f"  — {n.get('filePath','')}" if n.get('filePath') else ""))
        if len(node_ids) > count:
            lines.append(f"  ... and {len(node_ids)-count} more")
        return "\n".join(lines)

    # ── ua_tour ───────────────────────────────────────────────────────────
    elif action == "ua_tour":
        if not tour:
            return "[UA TOUR] No tour steps in this graph. Re-run /understand to generate one."
        lines = [f"[UA TOUR] {proj.get('name','?')} — {len(tour)} steps"]
        for step in sorted(tour, key=lambda s: s.get("order", 0)):
            lines.append(f"\n  Step {step.get('order','?')}: {step.get('title','?')}")
            lines.append(f"    {step.get('description','')[:120]}")
            nids = step.get("nodeIds", [])
            if nids:
                lines.append(f"    nodes: {', '.join(nids[:4])}"
                             + (" ..." if len(nids) > 4 else ""))
        return "\n".join(lines)

    else:
        return (f"[UA ERROR] Unknown action: {action!r}\n"
                f"  Valid: ua_info | ua_search | ua_node | ua_layer | ua_tour")


# ════════════════════════════════════════════════════════════════════════════
# UNIFIED DISPATCH
# ════════════════════════════════════════════════════════════════════════════

def find_blocks(text):
    """Return list of (tag, raw_json_str) tuples in document order."""
    results = []
    for m in MP_RE.finditer(text):
        results.append((m.start(), "mp", m.group(1).strip()))
    for m in UA_RE.finditer(text):
        results.append((m.start(), "ua", m.group(1).strip()))
    results.sort(key=lambda x: x[0])
    return [(tag, raw) for _, tag, raw in results]


def process(text):
    results = []
    for tag, raw in find_blocks(text):
        try:
            cmd = json.loads(raw)
        except json.JSONDecodeError as e:
            results.append(f"[{tag.upper()} PARSE ERROR] {e}\n  Raw: {raw[:120]}")
            continue
        try:
            if tag == "mp":
                results.append(dispatch_mp(cmd))
            else:
                results.append(dispatch_ua(cmd))
        except requests.HTTPError as e:
            results.append(f"[MP HTTP {e.response.status_code}] {e.response.text[:300]}")
        except Exception as e:
            results.append(f"[{tag.upper()} ERROR] {type(e).__name__}: {e}")
    return "\n\n".join(results) if results else None


# ════════════════════════════════════════════════════════════════════════════
# MAIN LOOP
# ════════════════════════════════════════════════════════════════════════════

def main():
    if not MEMORY_PLUGIN_TOKEN:
        print("ERROR: Set the MEMORY_PLUGIN_TOKEN environment variable before running.")
        print("  Windows: set MEMORY_PLUGIN_TOKEN=your_token_here")
        print("  Or create a .env file and load it before launching.")
        sys.exit(1)

    print("── MemoryPlugin + Understand-Anything Clipboard Watcher ─────────")
    print(f"  Poll: {POLL_INTERVAL}s   Fire delay: {FIRE_DELAY}s   Ctrl-C to stop")
    print("  Triggers: [mp] blocks (MemoryPlugin) and [ua] blocks (knowledge graphs)")
    print("  Copy ANYTHING ELSE within 2s to cancel the countdown.")
    print("─────────────────────────────────────────────────────────────────\n")

    try:
        last_seen = pyperclip.paste()
    except Exception:
        last_seen = ""
    last_result = ""

    while True:
        try:
            clip = pyperclip.paste()
        except Exception:
            time.sleep(POLL_INTERVAL)
            continue

        if clip == last_result or clip == last_seen:
            time.sleep(POLL_INTERVAL)
            continue

        last_seen = clip

        if not find_blocks(clip):
            time.sleep(POLL_INTERVAL)
            continue

        ts = datetime.datetime.now().strftime("%H:%M:%S")
        print(f"[{ts}] Block detected — firing in {FIRE_DELAY:.0f}s "
              "(copy anything else to cancel)...")

        cancelled = False
        for _ in range(int(FIRE_DELAY / 0.1)):
            time.sleep(0.1)
            try:
                current = pyperclip.paste()
            except Exception:
                continue
            if current != clip:
                print("  → Cancelled.\n")
                last_seen = current
                cancelled = True
                break

        if cancelled:
            continue

        result = process(clip)
        if result:
            ts2 = datetime.datetime.now().strftime("%H:%M:%S")
            print(f"[{ts2}] FIRED")
            print(result[:500] + ("..." if len(result) > 500 else ""))
            print("-> Result on clipboard.\n")
            pyperclip.copy(result)
            last_result = result
            last_seen = result

        time.sleep(POLL_INTERVAL)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\nWatcher stopped.")

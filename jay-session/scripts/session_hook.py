#!/usr/bin/env python3
"""session-manager 훅 (Stop / PreCompact / SessionStart 공용).

- Stop        : 방금 끝난 턴을 .claude/session/devlog.md 에 append (월별 롤오버)
- PreCompact  : 압축 직전 원본 transcript 위치를 devlog에 남김 (auto-compact 보험)
- SessionStart: /clear 직후 최신 handoff 를 새 세션 컨텍스트에 주입

devlog.md 가 없으면 Stop/PreCompact 는 아무것도 하지 않는다 (프로젝트별 opt-in).
자기검증: python3 session_hook.py --selftest
"""
import json
import os
import re
import sys
from datetime import datetime, timedelta  # timedelta: describe_age 인자 타입
from pathlib import Path

EDIT_TOOLS = {"Edit", "Write", "NotebookEdit", "MultiEdit"}
SYSTEM_TAG = re.compile(r"<(system-reminder|command-[a-z-]+|local-command-[a-z-]+)>.*?</\1>", re.S)


def session_dir(data):
    return Path(data.get("cwd") or os.getcwd()) / ".claude" / "session"


def _text(content):
    """message.content(문자열 또는 블록 리스트)에서 사람이 읽는 텍스트만 뽑는다."""
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return ""
    return "\n".join(b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text")


def load_transcript(path):
    p = Path(path or "")
    if not p.is_file():
        return []
    out = []
    for line in p.read_text(errors="replace").splitlines():
        line = line.strip()
        if line:
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                pass
    return out


def parse_turn(entries):
    """마지막 사용자 요청과 그 이후의 응답/도구 사용을 추린다."""
    start = None
    for i, e in enumerate(entries):
        if e.get("isSidechain") or e.get("type") != "user":
            continue
        if _text(e.get("message", {}).get("content")).strip():
            start = i
    if start is None:
        return None

    prompt = SYSTEM_TAG.sub("", _text(entries[start]["message"]["content"])).strip()
    if not prompt:
        return None

    replies, tools, files = [], [], []
    for e in entries[start + 1:]:
        if e.get("isSidechain") or e.get("type") != "assistant":
            continue
        for b in e.get("message", {}).get("content", []) or []:
            if not isinstance(b, dict):
                continue
            if b.get("type") == "text" and b.get("text", "").strip():
                replies.append(b["text"].strip())
            elif b.get("type") == "tool_use":
                tools.append(b.get("name", ""))
                path = (b.get("input") or {}).get("file_path")
                if b.get("name") in EDIT_TOOLS and path and path not in files:
                    files.append(path)
    return {"prompt": prompt, "reply": "\n\n".join(replies), "tools": tools, "files": files}


def render(turn, now):
    def clip(s, n):
        s = " ".join(s.split())
        return s if len(s) <= n else s[: n - 1] + "…"

    lines = [
        "",
        f"## {now:%Y-%m-%d %H:%M} — {clip(turn['prompt'], 60)}",
        f"**요청:** {clip(turn['prompt'], 400)}",
    ]
    if turn["reply"]:
        lines.append(f"**결과:** {clip(turn['reply'], 600)}")
    if turn["files"]:
        lines.append("**변경:** " + ", ".join(turn["files"]))
    if turn["tools"]:
        lines.append("**도구:** " + ", ".join(dict.fromkeys(turn["tools"])))
    return "\n".join(lines) + "\n"


def append_devlog(devlog, text, now=None):
    """월이 바뀌었으면 이전 달치를 떼어내고 새로 시작한다.

    devlog.md 존재 여부가 opt-in 플래그라, 파일명은 그대로 두고 과거만 분리한다.
    검색은 devlog*.md 를 glob 하면 된다.
    """
    now = now or datetime.now()
    if devlog.stat().st_size > 0:
        prev = datetime.fromtimestamp(devlog.stat().st_mtime)
        if (prev.year, prev.month) != (now.year, now.month):
            archive = devlog.with_name(f"devlog-{prev:%Y-%m}.md")
            if not archive.exists():
                devlog.rename(archive)
                devlog.touch()
    with devlog.open("a") as f:
        f.write(text)


def on_stop(data):
    devlog = session_dir(data) / "devlog.md"
    if not devlog.exists():
        return
    entries = load_transcript(data.get("transcript_path"))
    if not entries:
        return

    # 이미 기록한 지점 이후만 처리 — Stop 훅은 매 턴 실행되므로 커서가 없으면 전부 중복된다.
    state = devlog.parent / ".devlog-state"
    last = state.read_text().strip() if state.exists() else ""
    if last:
        for i, e in enumerate(entries):
            if e.get("uuid") == last:
                entries = entries[i + 1:]
                break
    if not entries:
        return

    turn = parse_turn(entries)
    if turn:
        append_devlog(devlog, render(turn, datetime.now()))
    if entries[-1].get("uuid"):
        state.write_text(entries[-1]["uuid"])


def on_precompact(data):
    """압축은 모델의 컨텍스트만 지우고 transcript 파일은 디스크에 남는다.
    그래서 보험으로 필요한 건 스냅샷이 아니라 '원본이 어디 있는지'다."""
    devlog = session_dir(data) / "devlog.md"
    if not devlog.exists():
        return
    trigger = data.get("trigger", "?")
    append_devlog(
        devlog,
        f"\n## {datetime.now():%Y-%m-%d %H:%M} — ⚠ 컨텍스트 압축 ({trigger})\n"
        f"**메모:** 이 지점에서 컨텍스트가 압축됨. 압축 전 전체 대화 원본: "
        f"`{data.get('transcript_path', '?')}`\n",
    )


def describe_age(delta):
    minutes = int(delta.total_seconds() // 60)
    if minutes < 60:
        return "방금"
    if minutes < 60 * 24:
        return f"{minutes // 60}시간 전"
    return f"{minutes // (60 * 24)}일 전"


def on_session_start(data):
    """대화가 지워진 직후, 가장 최근 handoff 를 새 컨텍스트에 물려준다.

    시간 제한을 두지 않는 대신 문서가 얼마나 오래됐는지를 함께 넘긴다.
    임의의 컷오프는 사용자가 외워야 할 규칙을 하나 늘릴 뿐이고, 오래된 문서인지는
    나이를 보고 판단하면 되는 일이다.

    clear 와 compact 는 상황이 다르다. clear 뒤에는 아무것도 없으니 브리핑하고
    다음 할 일을 물어야 하지만, compact 뒤에는 압축 요약이 이미 있고 작업이
    진행 중이다. 거기서 처음부터 브리핑하면 하던 일을 끊는다.
    """
    source = data.get("source")
    if source not in ("clear", "compact"):
        return
    files = sorted(session_dir(data).glob("handoff-*.md"), key=lambda p: p.stat().st_mtime)
    if not files:
        return
    latest = files[-1]
    age = describe_age(datetime.now() - datetime.fromtimestamp(latest.stat().st_mtime))
    if source == "clear":
        guidance = (
            f"검증 후 3~5줄로 브리핑하고 '다음에 할 일' 1번부터 시작할지 물어보세요. "
            f"다만 이 문서는 {age} 것이므로, 하루 이상 지났다면 사용자가 정말 이 작업을 "
            "이어서 하려는 게 맞는지부터 확인하세요 — 무관한 작업을 하려고 /clear 했을 수도 있습니다."
        )
    else:
        guidance = (
            "컨텍스트 압축 직후라 하던 작업이 그대로 이어지는 중입니다. "
            "이 문서는 압축 요약이 흘린 것을 메우는 참고 자료이지 새 지시가 아닙니다. "
            "브리핑하거나 다음 할 일을 다시 묻지 말고, 하던 일을 계속하세요. "
            "요약과 이 문서가 어긋나면 그때만 짚으세요."
        )
    print(json.dumps({"hookSpecificOutput": {
        "hookEventName": "SessionStart",
        "additionalContext": (
            f"이전 세션의 인계 문서입니다 ({latest}, {age} 작성).\n"
            "git 저장소면 git status / git log 로 이 문서가 지금도 유효한지 먼저 확인하세요. "
            "인계 문서는 쓰인 시점의 스냅샷이라 그 사이 다른 세션이 작업을 진행했을 수 있습니다.\n"
            + guidance + "\n\n---\n" + latest.read_text()
        ),
    }}))


HANDLERS = {"Stop": on_stop, "PreCompact": on_precompact, "SessionStart": on_session_start}


def main():
    try:
        data = json.load(sys.stdin)
    except Exception:
        return
    handler = HANDLERS.get(data.get("hook_event_name"))
    if handler:
        handler(data)


def selftest():
    import tempfile

    entries = [
        {"uuid": "a", "type": "user", "message": {"content": "<system-reminder>noise</system-reminder>토큰 만료 처리 추가해줘"}},
        {"uuid": "b", "type": "assistant", "message": {"content": [
            {"type": "tool_use", "name": "Edit", "input": {"file_path": "src/auth.py"}},
            {"type": "text", "text": "만료 검사 추가했습니다."},
        ]}},
        {"uuid": "c", "type": "assistant", "isSidechain": True, "message": {"content": [{"type": "text", "text": "서브에이전트 잡음"}]}},
    ]
    t = parse_turn(entries)
    assert t["prompt"] == "토큰 만료 처리 추가해줘", t["prompt"]
    assert t["files"] == ["src/auth.py"], t["files"]
    assert "서브에이전트" not in t["reply"], t["reply"]
    out = render(t, datetime(2026, 8, 6, 17, 22))
    assert "## 2026-08-06 17:22 — 토큰 만료 처리 추가해줘" in out, out
    assert "**변경:** src/auth.py" in out, out
    assert parse_turn([{"uuid": "x", "type": "assistant", "message": {"content": []}}]) is None

    with tempfile.TemporaryDirectory() as d:
        log = Path(d) / "devlog.md"
        log.write_text("## 지난달\n")
        os.utime(log, (0, datetime(2026, 7, 20).timestamp()))
        append_devlog(log, "## 이번달\n", now=datetime(2026, 8, 6))
        assert (Path(d) / "devlog-2026-07.md").read_text() == "## 지난달\n"
        assert log.read_text() == "## 이번달\n", log.read_text()
        append_devlog(log, "## 또 이번달\n", now=datetime(2026, 8, 7))
        assert "지난달" not in log.read_text() and "또 이번달" in log.read_text()

    assert describe_age(timedelta(minutes=3)) == "방금"
    assert describe_age(timedelta(minutes=59)) == "방금"
    assert describe_age(timedelta(hours=5)) == "5시간 전"
    assert describe_age(timedelta(days=32, hours=2)) == "32일 전"
    print("ok")


if __name__ == "__main__":
    selftest() if "--selftest" in sys.argv else main()

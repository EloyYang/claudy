#!/usr/bin/env python3
"""
Buni Windows - Claude Code 훅 설치 스크립트
훅 스크립트를 %APPDATA%\Claude에 설치하고 settings.json을 업데이트합니다.
"""
import json, os, sys, shutil
from pathlib import Path

# 이벤트 파일: Windows TEMP
TEMP = Path(os.environ.get('TEMP', os.environ.get('TMP', 'C:/temp')))
EVENTS_FILE = TEMP / 'claude-companion-events.jsonl'

# Claude Code 설정 디렉터리
CLAUDE_DIR = Path.home() / '.claude'
SETTINGS   = CLAUDE_DIR / 'settings.json'

# ── 훅 스크립트 내용 ──────────────────────────────────────────

PRETOOL = f'''\
#!/usr/bin/env python3
import sys, json
try:
    d = json.load(sys.stdin)
    tool = d.get("tool_name", "tool")
    line = json.dumps({{"type": "tool_use", "tool": tool}})
    with open(r"{EVENTS_FILE}", "a", encoding="utf-8") as f:
        f.write(line + "\\n")
except Exception:
    pass
'''

POSTTOOL = f'''\
#!/usr/bin/env python3
import sys
try:
    sys.stdin.read()
    with open(r"{EVENTS_FILE}", "a", encoding="utf-8") as f:
        f.write('{{"type":"tool_done"}}\\n')
except Exception:
    pass
'''

NOTIFICATION = f'''\
#!/usr/bin/env python3
import sys, json
try:
    d = json.load(sys.stdin)
    msg = d.get("message", "알림")[:120]
    line = json.dumps({{"type": "notification", "message": msg}})
    with open(r"{EVENTS_FILE}", "a", encoding="utf-8") as f:
        f.write(line + "\\n")
except Exception:
    pass
'''

STOP = f'''\
#!/usr/bin/env python3
import sys
try:
    sys.stdin.read()
    with open(r"{EVENTS_FILE}", "a", encoding="utf-8") as f:
        f.write('{{"type":"done"}}\\n')
except Exception:
    pass
'''

PERMISSION = f'''\
#!/usr/bin/env python3
import sys, json, uuid, os, time
from pathlib import Path

TEMP = Path(r"{TEMP}")
EVENTS = Path(r"{EVENTS_FILE}")

try:
    d = json.load(sys.stdin)
    req_id = str(uuid.uuid4())
    cmd = d.get("tool_name", "") + " " + json.dumps(d.get("tool_input", {{}}))
    line = json.dumps({{"type": "permission_request", "id": req_id, "message": cmd[:300]}})
    with EVENTS.open("a", encoding="utf-8") as f:
        f.write(line + "\\n")
    # 결정 파일 대기 (최대 60초)
    decision_file = TEMP / f"claude-companion-decision-{{req_id}}"
    for _ in range(120):
        if decision_file.exists():
            decision = decision_file.read_text().strip()
            decision_file.unlink(missing_ok=True)
            if decision == "deny":
                sys.exit(1)   # Claude Code에 거부 신호
            sys.exit(0)
        time.sleep(0.5)
    sys.exit(1)   # 타임아웃 = 거부
except Exception:
    sys.exit(0)
'''

SCRIPTS = {
    'companion-pretool.py':      PRETOOL,
    'companion-posttool.py':     POSTTOOL,
    'companion-notification.py': NOTIFICATION,
    'companion-stop.py':         STOP,
    'companion-permission.py':   PERMISSION,
}

def main():
    CLAUDE_DIR.mkdir(parents=True, exist_ok=True)
    EVENTS_FILE.parent.mkdir(parents=True, exist_ok=True)
    EVENTS_FILE.touch(exist_ok=True)

    # 훅 스크립트 작성
    for name, content in SCRIPTS.items():
        path = CLAUDE_DIR / name
        path.write_text(content, encoding='utf-8')
        print(f'  ✓ {path}')

    # settings.json 업데이트
    if SETTINGS.exists():
        try:
            with SETTINGS.open(encoding='utf-8') as f:
                settings = json.load(f)
        except json.JSONDecodeError:
            settings = {}
        # 백업
        shutil.copy(SETTINGS, str(SETTINGS) + '.buni-backup')
    else:
        settings = {}

    python = sys.executable

    def hook(script):
        return {'type': 'command',
                'command': f'"{python}" "{CLAUDE_DIR / script}"; exit 0'}

    new_hooks = {
        'PreToolUse':   [{'matcher': '', 'hooks': [hook('companion-pretool.py')]}],
        'PostToolUse':  [{'matcher': '', 'hooks': [hook('companion-posttool.py')]}],
        'Notification': [{'matcher': '', 'hooks': [hook('companion-notification.py')]}],
        'Stop':         [{'matcher': '', 'hooks': [hook('companion-stop.py')]}],
    }

    existing = settings.get('hooks', {})
    for event, entries in new_hooks.items():
        prev = [e for e in existing.get(event, [])
                if not any('companion-' in str(h) for h in e.get('hooks', []))]
        existing[event] = prev + entries
    settings['hooks'] = existing

    with SETTINGS.open('w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2, ensure_ascii=False)
    print(f'  ✓ {SETTINGS}')
    print()
    print('훅 설치 완료.')

if __name__ == '__main__':
    main()

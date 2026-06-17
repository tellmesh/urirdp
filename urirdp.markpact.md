# UriPack: urirdp

Self-contained Markpact — definitions, full source, run config. Unpack & run: `urisys markpact run urirdp/urirdp.markpact.md --as service` (writes `.markpact/`).

```yaml markpact:pack
apiVersion: urisys.io/v1
kind: UriPack
metadata:
  id: urirdp-pack
  version: 1.0.0
  language: python
description: RDP session and X11 display queries for urirdp-docker.
schemes:
- rdp
capabilities:
- id: rdp.session.status
  uri: rdp://{host}/session/query/status
  kind: query
  operation: rdp.session.status
  handler: python://urirdp.handlers:status
  side_effects: false
  approval: not_required
- id: rdp.session.display
  uri: rdp://{host}/session/query/display
  kind: query
  operation: rdp.session.display
  handler: python://urirdp.handlers:display
  side_effects: false
  approval: not_required
- id: rdp.display.status
  uri: rdp://{host}/display/query/status
  kind: query
  operation: rdp.display.status
  handler: python://urirdp.handlers:display_status
  side_effects: false
  approval: not_required
- id: rdp.session.prepare_target
  uri: rdp://{host}/session/command/prepare-target
  kind: command
  operation: rdp.session.prepare_target
  handler: python://urirdp.handlers:prepare_target
  side_effects: true
  approval: required
- id: rdp.session.dismiss_target
  uri: rdp://{host}/session/command/dismiss-target
  kind: command
  operation: rdp.session.dismiss_target
  handler: python://urirdp.handlers:dismiss_target
  side_effects: true
  approval: required
policy:
  default: deny_mutations_without_approval
runtime:
  default_environment: mock
  supports:
  - mock
  - local
  - docker
```

```yaml markpact:run
modes:
- pack
- service
- flow
- interface
- adapter
default: service
scheme: rdp
service:
  port: 8790
  wire: POST /uri/call
flow:
  ids:
  - rdp-kvm-smoke
adapter:
  wire: POST /uri/call
  events: GET /events
```

```python markpact:module path=urirdp/__init__.py
from __future__ import annotations

from .routes import manifest_path, register

__version__ = "0.1.0"
__all__ = ["register", "manifest_path", "__version__"]
```

```python markpact:module path=urirdp/display.py
from __future__ import annotations

import os
import subprocess
from pathlib import Path
from typing import Any


def config_value(context: dict[str, Any], key: str, default=None):
    cfg = context.get("config") or {}
    return cfg.get(key, default)


def detect_display(context: dict[str, Any]) -> str:
    # Priority: explicit context, env, config default, scan X sockets.
    if context.get("display"):
        return str(context["display"])
    if os.environ.get("URISYS_KVM_DISPLAY"):
        return os.environ["URISYS_KVM_DISPLAY"]
    if os.environ.get("URISYS_RDP_DISPLAY"):
        return os.environ["URISYS_RDP_DISPLAY"]
    if os.environ.get("DISPLAY"):
        return os.environ["DISPLAY"]
    default = config_value(context, "default_display")
    if default:
        return str(default)
    sockets = sorted(Path("/tmp/.X11-unix").glob("X*"))
    if sockets:
        return ":" + sockets[0].name[1:]
    return ":10"


def base_env(context: dict[str, Any]) -> dict[str, str]:
    env = os.environ.copy()
    env["DISPLAY"] = detect_display(context)
    xauth = (
        context.get("xauthority")
        or os.environ.get("XAUTHORITY")
        or config_value(context, "xauthority")
    )
    if not xauth:
        user = config_value(context, "session_user", "urisys")
        candidate = Path(f"/home/{user}/.Xauthority")
        if candidate.exists():
            xauth = str(candidate)
    if xauth:
        env["XAUTHORITY"] = str(xauth)
    return env


def allow_real(context: dict[str, Any]) -> bool:
    return bool(context.get("allow_real") or os.environ.get("URISYS_ALLOW_REAL") == "1")


def run_cmd(args: list[str], context: dict[str, Any], *, timeout: int = 20) -> subprocess.CompletedProcess:
    return subprocess.run(args, env=base_env(context), text=True, capture_output=True, timeout=timeout, check=False)


def ensure_screenshot_dir(context: dict[str, Any]) -> Path:
    path = config_value(context, "screenshot_dir", "data/screenshots")
    p = Path(path)
    p.mkdir(parents=True, exist_ok=True)
    return p
```

```python markpact:module path=urirdp/handlers.py
from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Any

from urirdp.display import allow_real, base_env, detect_display, run_cmd


def _service_status(name: str) -> dict[str, Any]:
    try:
        res = subprocess.run(['pgrep', '-a', name], text=True, capture_output=True, check=False)
        return {'running': res.returncode == 0, 'processes': [x for x in res.stdout.splitlines() if x.strip()]}
    except Exception as exc:
        return {'running': False, 'error': str(exc)}


def status(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    return {
        'host': context.get('params', {}).get('host'),
        'xrdp': _service_status('xrdp'),
        'xrdp_sesman': _service_status('xrdp-sesman'),
        'display': detect_display(context),
        'rdp_port': int(os.environ.get('RDP_PORT', '3389')),
        'uri_port': int(os.environ.get('URISYS_RDP_PORT', '8795')),
        'hint': 'Connect with an RDP client, then run kvm://... calls against the active X session.',
    }


def display(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    display_name = detect_display(context)
    res = run_cmd(['xdpyinfo'], {**context, 'display': display_name}, timeout=5)
    return {
        'display': display_name,
        'available': res.returncode == 0,
        'xdpyinfo_first_lines': res.stdout.splitlines()[:8],
        'error': res.stderr.strip() if res.returncode != 0 else None,
    }


def display_status(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    display_name = detect_display(context)
    socket_path = Path('/tmp/.X11-unix') / f"X{display_name.lstrip(':')}"
    display_exists = socket_path.exists()
    xdpyinfo_ok = False
    if display_exists:
        xdpyinfo_ok = run_cmd(['xdpyinfo'], context, timeout=5).returncode == 0

    screenshot_ok = False
    if allow_real(context) and xdpyinfo_ok:
        probe = Path('/tmp/urirdp-probe.png')
        shot = run_cmd(['scrot', str(probe)], context, timeout=10)
        screenshot_ok = shot.returncode == 0 and probe.exists() and probe.stat().st_size >= 128
        probe.unlink(missing_ok=True)

    return {
        'display': display_name,
        'display_exists': display_exists,
        'xdpyinfo_ok': xdpyinfo_ok,
        'screenshot_ok': screenshot_ok,
        'ready': display_exists and xdpyinfo_ok,
    }


def _dismiss_stale_targets(context: dict[str, Any]) -> int:
    """Close bootstrap or stale zenity dialogs blocking the RDP desktop."""
    if context.get('dry_run') or not allow_real(context):
        return 0
    closed = 0
    for title in ('Automation Target', 'TellMesh Demo'):
        res = run_cmd(['xdotool', 'search', '--name', title], context, timeout=5)
        for wid in res.stdout.splitlines():
            wid = wid.strip()
            if not wid:
                continue
            run_cmd(['xdotool', 'windowclose', wid], context, timeout=3)
            closed += 1
    if closed == 0:
        res = run_cmd(['xdotool', 'search', '--class', 'Zenity'], context, timeout=5)
        for wid in res.stdout.splitlines()[:4]:
            wid = wid.strip()
            if not wid:
                continue
            run_cmd(['xdotool', 'windowclose', wid], context, timeout=3)
            closed += 1
    if closed:
        time.sleep(0.5)
    return closed


def dismiss_target(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    display_name = detect_display(context)
    if context.get('dry_run') or not allow_real(context):
        return {'dismissed': True, 'driver': 'mock', 'display': display_name, 'closed': 0}
    closed = _dismiss_stale_targets(context)
    return {'dismissed': True, 'display': display_name, 'closed': closed}


def prepare_target(payload: dict[str, Any], context: dict[str, Any]) -> dict[str, Any]:
    display_name = detect_display(context)
    kind = str(payload.get('kind') or 'info')
    text = str(payload.get('text') or 'OK')
    if context.get('dry_run') or not allow_real(context):
        return {'prepared': True, 'driver': 'mock', 'display': display_name, 'text': text, 'kind': kind}

    _dismiss_stale_targets(context)
    env = base_env(context)
    if kind == 'form':
        subprocess.Popen(
            [
                'zenity', '--forms',
                '--title=TellMesh Demo',
                '--text=Fill the form',
                '--add-entry=Name',
                '--ok-label=Submit',
                '--width=420',
                '--height=220',
            ],
            env=env,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        time.sleep(2.0)
        run_cmd(['xdotool', 'search', '--name', 'TellMesh Demo', 'windowactivate'], context, timeout=5)
        return {'prepared': True, 'display': display_name, 'kind': 'form', 'driver': 'zenity-forms'}

    subprocess.Popen(
        [
            'zenity', '--info',
            '--title=Automation Target',
            f'--text={text}',
            '--no-wrap',
            '--width=320',
            '--height=120',
        ],
        env=env,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    run_cmd(['xdotool', 'search', '--name', 'Automation Target', 'windowactivate'], context, timeout=5)
    return {'prepared': True, 'display': display_name, 'text': text, 'driver': 'zenity', 'kind': kind}
```

```python markpact:module path=urirdp/routes.py
from __future__ import annotations

from importlib.resources import files

from urisysedge.manifest import register_manifest_file


def manifest_path():
    return files(__package__).joinpath("manifest.yaml")


def register(runtime):
    register_manifest_file(runtime, manifest_path())
```

```yaml markpact:flow id=rdp-kvm-smoke
flow:
  id: rdp-kvm-smoke
  description: RDP session status, screenshot, OCR, click OK (urirdp-docker stack).

defaults:
  approved: true
  dry_run: true

do:
  - rdp://local/session/query/status
  - rdp://local/session/command/prepare-target
  - kvm://local/monitor/primary/query/screenshot
  - ocr://local/image/latest/query/text
  - kvm://local/task/command/click-text:
      text: OK
```

```markdown markpact:docs
# urirdp

`rdp://` URI capability pack — session status, X11 display probes, zenity target prep/dismiss.

## Layout

~~~text
urirdp/
  urirdp/manifest.yaml
  urirdp/routes.py
  urirdp/handlers.py
  urirdp/display.py   # X11 display helpers (shared with urikvm)
~~~

Execution packs (`kvm`, `him`, `ocr`, `llm`, …) are **separate repos**. HTTP composition: [`urirdpedge`](../urirdpedge/). Docker demo: [`urirdp-docker`](../urirdp-docker/).

Licensed under Apache-2.0.
```


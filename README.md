# urirdp

`rdp://` URI capability pack — session status, X11 display probes, zenity target prep/dismiss.

## Layout

```text
urirdp/
  urirdp/manifest.yaml
  urirdp/routes.py
  urirdp/handlers.py
  urirdp/display.py   # X11 display helpers (shared with urikvm)
```

Execution packs (`kvm`, `him`, `ocr`, `llm`, …) are **separate repos**. HTTP composition: [`urirdpedge`](../urirdpedge/). Docker demo: [`urirdp-docker`](../urirdp-docker/).

Licensed under Apache-2.0.

## Ekosystem TellMesh

Orchestrator: **[urisys](https://github.com/tellmesh/urisys)** · Mapa: **[MESH.md](https://github.com/tellmesh/urisys/blob/main/docs/MESH.md)** · Model: **[ECOSYSTEM.md](https://github.com/tellmesh/urisys/blob/main/docs/ECOSYSTEM.md)**

| Pole | Wartość |
|------|---------|
| **Warstwa** | Capability pack |
| **Scheme** | `rdp://` |
| **Zależność** | `uricontrol>=0.1.8` |
| **Edge** | urirdpedge |
| **Port** | 8795 |

Runtime edge: **`uri_control.edge`** w pakiecie **`uricontrol`** (legacy PyPI `uricore` / `urisysedge` usunięty 2026-06).
Resolver intencji: **`uriresolver`** (`uri_resolver`) + transport w **`uritransport`**; policy gate: **`uriguard`** (`uri_guard`).

<!-- end-ecosystem -->

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

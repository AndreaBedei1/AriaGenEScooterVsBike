# data/processed - analysis outputs (NOT versioned)

Written by `python -m ariagen_escooter run <session_dir>`:

```
processed/<session_id>/<recording_id>/report.json          deterministic summary
processed/<session_id>/<recording_id>/trimming.json        trimming decision and timestamps
processed/<session_id>/<recording_id>/effective_config.yaml
processed/<session_id>/<recording_id>/run_info.json        non-deterministic run metadata
processed/<session_id>/<recording_id>/tables/*.csv         metric tables
processed/<session_id>/<recording_id>/figures/*.png        diagnostic figures
processed/_study/                                          output of `aggregate`
```

Outputs of synthetic sessions also land here and are marked `synthetic: true`.

# data/raw - raw identifiable data (NOT versioned)

One folder per session, created with `python -m ariagen_escooter new-session --participant P001`:

```
raw/P001_S01/manifest.yaml
raw/P001_S01/P001_S01_R01/recording.vrs
raw/P001_S01/P001_S01_R01/mps/...            (only if MPS is used - see docs/privacy_pipeline.md)
raw/P001_S01/P001_S01_R01/external_gps.csv   (optional external logger)
```

Access restricted to authorised study staff. Never copy these files to shared drives,
e-mail or cloud services that are not covered by the data management plan.

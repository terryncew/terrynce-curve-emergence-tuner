# Author-derived data intake

This directory accepts measurements, not pictures. A returned author bundle
stays outside Git and must contain:

```text
bundle_manifest.json
velocity_observations.csv
terminus_observations.csv
control_registry.csv
```

Validate it with:

```bash
python experiments/terrynce_glacier_001/author_intake/validate_author_bundle.py \
  --bundle experiments/terrynce_glacier_001/author_intake/inbox/author-bundle \
  --output /tmp/AUTHOR_BUNDLE_RECEIPT.json
```

Malformed provenance or a hash mismatch exits nonzero. A genuine but incomplete
bundle exits successfully with `VALID_BUT_NOT_READY`; missing evidence remains
visible instead of being confused with corrupt evidence. Use `--require-ready`
only for the eventual frozen headline run.

## CSV contract

`velocity_observations.csv`

```text
glacier_id,interval_start_utc,interval_end_utc,profile_point_id,position_m_along_flowline,zone,along_flow_displacement_m,along_flow_velocity_m_per_day,source_product
```

Flow distance increases downstream. `zone` is `UPSTREAM` or `TERMINUS` and
must come from a source-frozen profile map rather than outcome-aware clustering.
Velocity is checked against displacement divided by interval duration.

`terminus_observations.csv`

```text
glacier_id,observed_at,terminus_position_m,source_product
```

`control_registry.csv`

```text
glacier_id,latitude,longitude,detached,control_source
```

Control exposure is computed from the union of actual velocity-observation
intervals. A five-year registry span with three measurements does not magically
become five observed glacier-years.


# elm327-vehicle-profiles

Vehicle profiles for [universal_elm327_logger](../../../universal-elm327-logger).
The app fetches them over HTTPS, so a profile change reaches the phone without
rebuilding or reinstalling anything.

A profile is data, not code: which signals to poll, how to decode them, which
diagnostic session and read-mode a signal needs, and which memory regions a
region-read may capture.

## Why this is a separate repository

The profile changes far more often than the app, and it has more than one
consumer. Keeping it here gives it one source of truth, its own history, and a
version that can be recorded alongside captured data — so months later you can
still answer which profile produced a given CSV.

## Layout

```
manifest.json                                   generated index — do not hand-edit
cars/
  Ford-Kuga/
    profile.json                                id, label, minimum app schema
    signalsets/v3/
      default.json                              OBDb upstream — do not modify
      extensions.json                           additive layer: sessions, read-modes,
                                                periodic RAM reads, memory regions
tools/build_manifest.py                         regenerates and verifies manifest.json
```

`default.json` follows the OBDb schema. `extensions.json` carries everything OBDb
does not model; its schema is documented in the app repository under
`docs/EXTENSIONS_SCHEMA.md`, with a worked walkthrough in
`docs/PROFILE_AUTHORING_GUIDE.md`. The schema is defined by the parser, so it is
documented next to the parser rather than copied here.

## The manifest is generated, never written by hand

`manifest.json` lists every profile with a content hash per file and a `revision`
that changes if and only if the content changes. The client fetches it first,
compares revisions, downloads only what moved, and verifies the hash afterwards.

Nothing here depends on an author remembering to bump a version — that is
deliberate. This repository exists because the same profile previously lived in
two places and silently drifted apart.

After editing any profile:

```
python tools/build_manifest.py
```

CI runs `--check` and fails the push if the manifest is stale, and parses every
JSON file so a syntax error is caught here rather than by a phone in a garage
with no connectivity.

## Adding a vehicle

1. Create `cars/<Make>-<Model>/signalsets/v3/default.json` (from OBDb upstream if
   it exists there, otherwise hand-written).
2. Add `extensions.json` for anything OBDb cannot express. Optional.
3. Add `profile.json` with a stable `id` and a human `label`.
4. Regenerate the manifest and commit.

Raise `minAppSchema` when a profile starts using a feature older app versions
cannot parse. An app that is too old then reports that it needs updating instead
of loading half a profile.

## Compatibility

The app ships a bundled copy of these profiles so it works on first launch and
whenever the network is unavailable. A downloaded profile overlays the bundled
one; if a download is missing, stale or fails verification, the bundled copy
stands. A bad publish here must never leave the app without a working profile.

## License

GPL-3.0, matching the application.

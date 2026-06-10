# Automata Simulator

Interactive Flutter simulator for CSC-340 Theory of Automata at Namal University Mianwali.

The app follows the project proposal in `docs/TOA_PROJECT_PROPOSAL.pdf` and provides a unified interface for:

- DFA construction, dragging states, start/accept markers, transition table, string testing, trace stepping, minimization, and JSON save/load.
- NFA and transition graph execution with epsilon-closure, parallel active states, and NFA to DFA subset construction.
- Moore and Mealy machines with output-string tracing.
- PDA simulation with stack visualization for the classic `a^n b^n` language.
- CFG editor with leftmost/rightmost derivation, parse frontier display, and bounded ambiguity probing.
- Turing machine simulation with tape window, read/write head, and bounded halt/loop handling.
- Glossary module for core CSC-340 notation.

## Run Locally

```powershell
flutter pub get
flutter run -d chrome
```

For a local release preview:

```powershell
flutter build web --release
python -m http.server 8080 --directory build/web
```

## Verify

```powershell
flutter analyze
dart run tool/core_smoke_test.dart
flutter build web --release --base-href /automata-simulator/
```

## Deploy

The GitHub Actions workflow in `.github/workflows/deploy.yml` builds Flutter Web with:

```powershell
flutter build web --release --base-href /automata-simulator/
```

It then deploys the result to GitHub Pages and uploads an Android APK artifact from the same source tree.

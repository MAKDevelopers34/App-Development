# CFG to CNF Converter

A Flutter app for converting a context-free grammar into Chomsky Normal Form.

## Run Locally

```powershell
flutter run -d chrome
```

For a local web server:

```powershell
flutter run -d web-server --web-hostname 127.0.0.1 --web-port 8080
```

## Input Format

```text
S -> A B | a
A -> epsilon | b
```

Use `->` for productions, `|` for alternatives, and `epsilon` for the empty string.

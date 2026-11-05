# Deployable build — Windows executable (SCRUM-62)

**Decision.** The plan offered "PyInstaller exe **or** deploy backend to cloud". QuMail is a desktop
client whose only backend is the Key Manager; in a real deployment the KM is the customer's QKD
appliance on the local network, not a public cloud service, and publishing key material to a free
cloud tier would contradict the security model. The deliverable is therefore a **portable Windows
build**: `QuMail.exe` (client) + `QuMail-KM.exe` (simulator), no Python needed on the target PC.

## Build

```cmd
packaging\build_exe.bat
```

produces

```
dist\
  QuMail\QuMail.exe          desktop client (windowed)
  QuMail-KM\QuMail-KM.exe    Key Manager simulator (console, port 5000)
  START_QUMAIL.bat           starts both
  README_DIST.txt            end-user notes
```

Zip `dist\` and share — tested on a machine without Python installed (see checklist below).

CI also builds it: workflow job **Windows exe (PyInstaller)** runs on `windows-latest` for every
push to `develop`/`main` and uploads `QuMail-windows-x64.zip` as an artifact (Actions → run → Artifacts).

## How it works

| Piece | Why |
|---|---|
| `packaging/qumail.spec` | two `Analysis` blocks → two apps from one build; `collect_all("customtkinter")` bundles the theme JSON/fonts; Level 2/3/4 modules listed as hidden imports because `envelope.load_levels()` imports them dynamically |
| `km_simulator.py` | when frozen, `keybank.csv` is kept **next to the exe** (`sys.executable`) instead of the temp unpack dir, so keys survive restarts |
| `console=False` for the client | no black console window behind the GUI |
| one-folder (not one-file) | starts in < 1 s; one-file mode unpacks 60 MB to %TEMP% on every start and triggers more antivirus heuristics |
| `.gitignore` | `build/`, `dist/`, `*.spec` ignored, **except** `packaging/*.spec` |

## Clean-machine checklist

- [ ] Copy `dist\` to a PC/VM without Python → `START_QUMAIL.bat`
- [ ] KM console shows `Running on http://127.0.0.1:5000`
- [ ] Login → *Test* → "KM OK — 100 keys available"
- [ ] Send Level 2 mail with an attachment to yourself → Refresh → decrypts
- [ ] Close both, start again → key count continues (keybank.csv persisted)
- [ ] SmartScreen "Run anyway" needed once (unsigned build — code signing is out of scope)

## Size / timings (reference)

| | |
|---|---|
| `dist\QuMail` | ≈ 45 MB (Tk + customtkinter + pycryptodome) |
| `dist\QuMail-KM` | ≈ 15 MB (Flask) |
| Build time | ≈ 2 min on a laptop, ≈ 4 min on the CI runner |
| Cold start | < 1 s (one-folder) |

# OptionLab — GitHub and Release Checklist

## Before staging

- [ ] Confirm the full Python suite passes in the intended virtual environment.
- [ ] Run `cmake --build build`.
- [ ] Run `ctest --test-dir build --output-on-failure`.
- [ ] Run `python -m pip check`.
- [ ] Start the local dashboard and verify the key workflow.
- [ ] Confirm `.env` contains a local secret and is not staged.
- [ ] Confirm `.env.example` has only a placeholder.
- [ ] Confirm `data/cache/` is ignored.
- [ ] Confirm raw and normalized NSE contract metadata are ignored.
- [ ] Confirm `build/`, `.venv/`, `__pycache__/`, `*.pyc` and `*.exe` are ignored.
- [ ] Review all README commands against the scripts' actual CLI arguments.
- [ ] Add a deliberate license file only after choosing the intended license.

## Before the first commit

```powershell
git status --short
git check-ignore -v .env .venv/ build/ optionlab_engine.exe data/cache/
git ls-files -- .env .venv build optionlab_engine.exe
```

The last command should produce no output for those paths. If any sensitive file was committed in an earlier commit, `.gitignore` alone is not enough; remove it from repository history and rotate the exposed credential.

## Stage and inspect

```powershell
git add .
git diff --cached --name-only
git status --short
```

Review every staged filename. Do not proceed if `.env`, downloaded data, generated executables, virtual environments or build products appear.

## First commit

```powershell
git commit -m "Initial release: OptionLab pricing and analysis platform"
```

Add the remote repository URL only after creating the intended GitHub repository. Do not invent or reuse a remote URL from an example.

## Release notes to disclose

- Local development configuration; `run.py` uses Flask debug mode and loopback binding.
- Requires a locally configured TejHQ API key and permitted data access.
- Requires a suitable imported NSE F&O contract-master snapshot.
- No option-chain price ingestion, implied-volatility inversion or trading/execution.
- Strategy prices are theoretical BSM values and omit transaction costs and margin.
- No license is provided unless an explicit `LICENSE` file is added.

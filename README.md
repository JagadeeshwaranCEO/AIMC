# Analog Compute Runtime (ACR) — Day 1

A hardware-agnostic runtime that sits between PyTorch and analog
in-memory hardware (RRAM/PCM/memristor), hiding device noise, drift,
and asymmetric nonlinearity behind a stable software interface.

Day 1 goal: get a real vertical slice running - emulator, profiler,
pulse compiler, and dashboard - built in parallel on two machines and
glued together by one shared JSON contract, so nobody sits idle
waiting on someone else's code.

## Layout

```
acr/
  runtime/
    emulator.py         # software surrogate for an analog memory cell
    profiler.py          # characterizes cells -> device_profile.json
    pulse_compiler.py     # target conductance -> pulse sequence (open-loop)
    closed_loop.py         # measure -> correct -> repeat, wraps pulse_compiler
  dashboard/
    app.py                # Streamlit dashboard
    mock_data.py           # fake device_profile.json, same schema as the real one
  schemas/
    device_profile.schema.json   # the contract both sides must respect
  tests/
    smoke_test.py          # emulate -> profile -> compile -> check convergence
    test_pulse_compiler.py # focused unit tests, owned by the dashboard track
```

## Track A — Mac (runtime core)

```
cd acr
python3 runtime/profiler.py
python3 tests/smoke_test.py
```

Zero third-party dependencies - both scripts are pure standard library.
`profiler.py` writes `device_profile.json` into the `acr/` folder.
That file is the handoff artifact for Track B.

## Track B — Windows (dashboard + pulse compiler)

```
cd acr
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python dashboard\mock_data.py
streamlit run dashboard/app.py
```

This works fully offline from Track A. `mock_data.py` generates a fake
`mock_device_profile.json` with the same fields the real profiler
produces, so the dashboard has something real to render immediately,
without waiting on the Mac side.

### Continuing today: closed-loop control

```
python3 tests/test_pulse_compiler.py
python3 runtime/closed_loop.py
```

`closed_loop.py` wraps `compile_pulse()` in a measure -> correct ->
repeat loop instead of trusting one blind, upfront plan. It's built
and tested against `FakeCell`, a tiny mock with the same `.read()` /
`.apply_pulse()` interface as the real `AnalogCell` - so this is fully
ownable today, no emulator needed. Running it prints a real open-loop
vs. closed-loop comparison under a deliberately wrong calibration
profile:

```
open-loop:   final=0.4956  error=0.2044  pulses=21
closed-loop: final=0.6993  error=0.0007  pulses=50
```

**Remaining task:** wire `closed_loop_program(cell, profile, target_g)`
into `dashboard/app.py` so the "Compile pulse plan" panel can show
open-loop and closed-loop trajectories side by side (two lines on the
same `st.line_chart`, or two separate charts). Use `FakeCell` in place
of a real cell for now, seeded with the currently-selected row's
profile values, so it's testable without the Mac's data. That's the
one piece still open on this track.

## Day 2 merge

Copy the Mac-generated `device_profile.json` into the same `acr/`
folder on the Windows machine (git push/pull is easiest) and restart
the dashboard. Nothing in `app.py` needs to change - it already looks
for `device_profile.json` before falling back to mock data - because
both sides were built against `schemas/device_profile.schema.json`
from the start.

## Explicitly out of scope for Day 1

- 2D crossbar (this models one row of cells)
- Real hardware-in-the-loop (MCU/DAC/ADC) - pure software emulation only
- Closed-loop control wired into the dashboard - the control logic
  itself exists and is tested (`runtime/closed_loop.py`), but the
  dashboard still only visualizes the open-loop path
- Calibration Engine as its own module - the profiler currently folds
  fitting directly into itself

Natural next additions, roughly in that order:
1. Wire `closed_loop.py` into the dashboard (see above - this is the
   one item still open)
2. Split calibration fitting out of the profiler into its own module
3. Extend `AnalogCrossbar` from a 1D row to a full 2D array

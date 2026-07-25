# ACR (Analog Compute Runtime) - Agent Instructions

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run tests (no pytest - use direct execution)
python tests/test_critical.py       # 23 bug-prevention tests
python tests/test_comprehensive.py  # 85 module tests
python tests/test_acr_revolution.py # 47 ACR Revolution tests
python tests/test_holy_trinity.py   # 29 Holy Trinity tests
python tests/test_acr_runtime.py    # 42 unified API tests
```

**Total: 226 tests. No linting/typechecking configured.**

## Architecture

### Import Pattern (Critical)
Runtime modules import each other using **bare names** (e.g., `from emulator import AnalogCell`). There is no `pip install -e .` or package setup. Tests add `runtime/` to `sys.path` manually:

```python
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "runtime"))
```

### Package Boundaries
- `runtime/` - Core runtime (28 Python files, empty `__init__.py`)
- `tests/` - Test suite (8 files, custom framework)
- `experiments/` - Experimental validation scripts
- `dashboard/` - Streamlit visualization

### Key Files (Bottom to Top)
1. `emulator.py` - `AnalogCell`, `AnalogCrossbar2D` (physical emulation)
2. `hal.py` - `RRAMDevice`, `PCMDevice`, `FeFETDevice` (hardware abstraction)
3. `vcm.py` - `VirtualConductanceManager` (weight-to-conductance mapping)
4. `isa.py` - `OpCode`, `Instruction`, `InstructionSet` (instruction architecture)
5. `device_manager.py` - `DeviceManager` (tile allocation, health tracking)
6. `scheduler.py` - `RuntimeScheduler` (instruction queue, maintenance injection)
7. `compensation_tick.py` - `CompensationTickCoprocessor` (core innovation)
8. `analog_training.py` - `AnalogLinear`, `AnalogMLP`, `AnalogTrainer` (PyTorch bridge)
9. `acr_revolution.py` - `ACR` class + complex-valued computation (legacy)
10. `acr_holy_trinity.py` - `ACR_Thermodynamic` (Langevin + Neural ODE + Crossbar, legacy)
11. `acr_runtime.py` - **`ACRRuntime`** (UNIFIED API - single entry point for all capabilities)

## Gotchas

### Dual Classes (Incompatible)
- `AnalogCell` exists in both `emulator.py` (real-valued) and `acr_revolution.py` (complex-valued)
- `CrossbarArray` exists in both `hal.py` and `acr_holy_trinity.py` (different APIs)
- `DeviceType` enum exists in both `hal.py` and `acr_revolution.py` (different values)
- `TickScheduler` exists in both `compensation_tick.py` and `tick_scheduler.py`
- `TikiTakaCorrector` exists in both `compensation_tick.py` and `tiki_taka.py`

### Weight Orientation
`AnalogLinear` transposes weights before programming:
```python
self.crossbar.program_conductances(g_conductance.T)  # Note the .T
```

### Gradient Transpose
`AnalogLinearFunction.backward` requires transpose for non-square layers:
```python
grad_input = grad_output @ g_tensor.T  # Not g_tensor
grad_weight = grad_output.T @ input    # Not input.T @ grad_output
```

### Testing Quirks
- **No pytest/unittest** - custom `TestResults` classes with `check()` helpers
- Tests are standalone scripts: `python tests/test_*.py`
- Some tests are stochastic (depend on random seeds)
- Exit code: `sys.exit(0 if success else 1)`

### Environment
- Python 3.10+
- No `.env` or environment variables required
- No Docker, CI/CD, Makefile, or pre-commit hooks
- Dashboard: `streamlit run dashboard/app.py`

## Current State (2026-07-26)

- **226 tests passing** (23 + 85 + 47 + 29 + 42)
- **Two critical bugs fixed** (backward transpose + weight sync)
- **API unified** (`runtime/acr_runtime.py` - `ACRRuntime` class)
- **Specification written** (`ACR_RUNTIME_SPEC_v1.md`)
- **Whitepaper written** (`WHITEPAPER.md`)
- **Project completion: 88%** (code 85%, tests 92%, spec 80%, whitepaper 85%)

## Git Conventions

- Commits: `feat:`, `docs:`, `fix:` prefix style
- Branch: `master` (main branch)
- Remote: `https://github.com/JagadeeshwaranCEO/AIMC.git`

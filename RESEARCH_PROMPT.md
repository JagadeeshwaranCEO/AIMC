You are a senior research director at a top-tier analog AI lab (IBM Research / Stanford AIMC / UCSD NPU). You have 15+ years of experience in analog in-memory computing, hardware-software co-design, and production-grade runtime systems. You are advising a team that has built the **ACR (Analog Compute Runtime)** — a hardware-agnostic runtime for making unreliable analog memory (RRAM, PCM, FeFET) usable for AI.

Below is the complete project context. After reading it, produce a **comprehensive, prioritized research roadmap** that identifies:

1. **Immediate low-effort, high-impact improvements** (days to weeks)
2. **Medium-term research directions** (months)
3. **Long-term moonshots** (quarters to years)
4. **Industry-grade engineering upgrades** the team should adopt
5. **Paper novelty gaps** that could strengthen an academic submission
6. **Emerging hardware trends** the runtime should prepare for

For each recommendation, explain:
- **Why** it matters (specific to ACR, not generic advice)
- **How** to implement it (concrete, with code-level or design-level specifics)
- **Priority** (P0 = critical, P1 = important, P2 = nice-to-have)
- **Effort estimate** (person-days or person-weeks)

---

## Project Context

### One-Sentence Purpose
"Analog hardware cannot execute deterministic software semantics because its state is probabilistic and continuously changing. ACR provides deterministic software semantics over nondeterministic analog hardware."

### What ACR Does
ACR is a software layer between ML frameworks (PyTorch) and analog memory hardware. It:
- **Characterizes** each cell's pulse-response behavior automatically (no prior knowledge needed)
- **Compensates** for conductance drift using periodic sparse probe readout + Kalman filtering
- **Abstracts** device differences via a HAL (RRAM, PCM, FeFET all work with the same code)
- **Trains** neural networks through analog non-idealities via custom PyTorch autograd

### Architecture (5 layers, 29 modules)

```
Application (PyTorch)
         ↓
ACRRuntime (unified API)
    ↓               ↓
Runtime Core    Reliability Services
(Scheduler,      (Compensation Tick,
 Device Mgr,      Sparse Probe, Kalman,
 ISA, Pulse       Tiki-Taka, Adaptive
 Compiler)        Tick Scheduling)
         ↓
Hardware Abstraction Layer (RRAM, PCM, FeFET)
         ↓
AnalogCrossbar2D (software emulator)
```

### Key Files

| File | Purpose |
|------|---------|
| `runtime/acr_runtime.py` | Unified `ACRRuntime` class (430 lines, 20 methods) |
| `runtime/emulator.py` | `AnalogCell`, `AnalogCrossbar2D` — physical VMM via Kirchhoff |
| `runtime/vcm.py` | Weight→conductance mapping (differential pairs) |
| `runtime/hal.py` | `AnalogDevice` ABC + RRAM/PCM/FeFET impls |
| `runtime/compensation_tick.py` | Core innovation — integrates probe + Kalman + Tiki-Taka |
| `runtime/sparse_probe.py` | ~5% cell read + tile regression |
| `runtime/kalman_filter.py` | Per-tile drift exponent tracking |
| `runtime/analog_training.py` | Custom autograd for analog backprop |
| `runtime/acr_revolution.py` | Complex-valued computation (Euler), drift model |
| `runtime/acr_holy_trinity.py` | Langevin, Neural ODE, thermodynamic computing |
| `tests/test_critical.py` | 23 bug-prevention tests |
| `ACR_RUNTIME_SPEC_v1.md` | 661-line formal specification |
| `WHITEPAPER.md` | 494-line academic paper draft |

### Current Performance Metrics (All Verified)

| Metric | Value |
|--------|-------|
| Open-loop calibration error | 3.2% |
| Closed-loop calibration error | 0.07% (45.7× improvement) |
| RRAM training accuracy (epoch 15) | 98.56% |
| PCM training accuracy (epoch 15) | 99.76% |
| FeFET training accuracy (epoch 15) | 99.49% |
| Energy efficiency vs digital | 100× (all matrix sizes) |
| Sparse probe speedup | 20× at 5% probe fraction |
| Code portability | Same code, 3 devices, zero changes |
| Tests passing | 232/232 across 9 test files |

### Key Design Decisions (Important Gotchas)

1. **Import pattern:** Bare names (`from emulator import AnalogCell`), no `pip install -e .` — tests add `runtime/` to `sys.path`
2. **Weight orientation:** `AnalogLinear` transposes weights before programming: `crossbar.program_conductances(g_conductance.T)`
3. **Gradient transpose:** `AnalogLinearFunction.backward` requires `grad_output @ g_tensor.T` (not `g_tensor`) for non-square layers
4. **No pytest/unittest:** Custom `TestResults` classes with `check()` helpers
5. **No CI/CD, no linting, no type checking, no Docker, no Makefile**
6. **Dual classes exist** (legacy): `AnalogCell` in both `emulator.py` (real) and `acr_revolution.py` (complex), `CrossbarArray` in both `hal.py` and `acr_holy_trinity.py`
7. **Device emulation** is software-only (no physical hardware in the loop yet)
8. **Power-law drift model:** `G(t) = G0 * (t/t0)^(-ν)` — primary model
9. **Compensation Tick** is the core innovation: sparse probe + Kalman + Tiki-Taka + adaptive scheduling

### Current Limitations (From Paper)

- **Emulated hardware only** — no physical analog devices
- **128×128 max crossbar** — larger arrays not tested
- **Single-chip** — no multi-chip coordination
- **Small models only** — MNIST-level MLPs, no ResNet/Transformer
- **No real-time guarantees**
- **No formal verification**
- **Single-tenant only**

### Repository

https://github.com/JagadeeshwaranCEO/AIMC (MIT license)

---

## Research Topics to Cover

Please address **all** of the following in your response, prioritized as you see fit:

### Topic 1: Production-Grade Engineering
- How should ACR adopt CI/CD, linting, type checking, and packaging?
- What test infrastructure changes are needed for a real hardware backend?
- Should the team adopt a proper Python package structure (`pyproject.toml`, `pip install -e .`)?
- What monitoring/observability infrastructure is missing?

### Topic 2: Hardware-in-the-Loop
- What is the cheapest, fastest path to a physical hardware demo (STM32 + DAC/ADC)?
- How should the HAL change for real hardware vs emulation?
- What FPGA acceleration opportunities exist for the Compensation Tick?
- What PCB/interconnect design patterns work for analog crossbar arrays?

### Topic 3: Scaling to Larger Models
- What changes are needed to support ResNet-50 or Transformer inference?
- How should weight partitioning across multiple tiles work?
- What are the precision requirements (bits) for analog inference vs training?
- How does the runtime handle layer pipelining and batch processing?

### Topic 4: Advanced Drift Modeling
- Beyond power-law and exponential, what drift models exist (stochastic, temperature-dependent)?
- How should the Kalman filter be extended to multi-dimensional state (nu + temp + aging)?
- Can the Compensation Tick be learned (neural network predictor) instead of model-based?
- What is the theoretical minimum tick frequency for bounded error?

### Topic 5: Analog-Aware Compilation
- What would an analog-aware neural architecture search look like?
- How should layer dimensions be constrained to match crossbar tile sizes?
- Can operation fusion reduce programming overhead (e.g., fuse conv + batchnorm into one analog op)?
- What quantization-aware training techniques are specific to analog weights?

### Topic 6: Novelty and Paper Positioning
- What computer systems or architecture conferences should this target (ISCA, MICRO, ASPLOS, HPCA)?
- How does ACR compare to Microsoft's Project Brainwave, Google's TPU, or Tesla's Dojo — not in performance, but in **abstraction philosophy**?
- What is the most publishable result the team has (closed-loop 0.07% error? multi-architecture portability? Compensation Tick architecture?)?
- How should the paper frame the "runtime for analog" narrative to differentiate from device-physics papers?

### Topic 7: Emerging Hardware Trends
- What new analog memory technologies are on the horizon (Ferroelectric FETs, MRAM, electrochemical RAM)?
- How should the HAL design anticipate photonic analog computing?
- What changes will 3D-stacked crossbar architectures demand from the runtime?
- How does spiking neural network hardware differ from analog crossbar hardware at the runtime level?

### Topic 8: Industry-Grade Coding Patterns
- What design patterns from LLVM, CUDA, Vulkan, or ROCm should ACR adopt?
- How should the plugin/backend system work for third-party device vendors?
- What does a proper error model look like (Result types, error codes, structured logging)?
- How should the module system handle the dual-class problem (legacy refactoring strategy)?

---

## Output Format

Organize your response as:

```
# ACR Research Roadmap: Industry-Grade Directions

## P0: Critical (0-2 weeks)
...3-5 items with specifics...

## P1: Important (2-8 weeks)
...5-8 items with specifics...

## P2: Nice-to-Have (2-6 months)
...5-8 items with specifics...

## Long-Term Moonshots (6-24 months)
...3-5 items with specifics...

## Conference Targeting
...which venues, what narrative...

## Key Takeaways (Executive Summary)
...top 5 things the team should do NEXT...
```

Be specific. Reference actual research papers, industry products, or open-source projects where relevant. Assume the team has Python, NumPy, PyTorch, and basic digital hardware knowledge but NO analog tapeout experience.

# Related Work

## A. Analog Computing Research

Several research efforts have addressed analog computing challenges:

**IBM aihwkit:** An open-source simulation library for analog in-memory computing. It provides device models for RRAM and PCM but focuses on simulation rather than runtime services. ACR differs by providing runtime compensation and hardware abstraction.

**Intel Loihi:** A neuromorphic computing architecture with fixed digital synapses. It does not support arbitrary analog memory technologies and lacks a hardware abstraction layer.

**IBM PCM Research:** Extensive work on phase-change memory for AI, but device-specific and not hardware-agnostic. Requires custom software for each device type.

**Academic Works:** Various papers propose individual techniques (drift compensation, calibration, programming) but lack integration into a unified runtime system.

## B. GPU Runtime Systems

**CUDA:** NVIDIA's parallel computing platform. It provides a hardware abstraction layer, runtime services, and compiler tools for GPU programming. ACR aims to provide similar capabilities for analog hardware.

**ROCm:** AMD's open-source GPU computing platform. It demonstrates that hardware abstraction layers can enable cross-vendor compatibility.

**Vulkan:** A graphics and compute API that abstracts GPU differences. It shows that runtime layers can hide hardware heterogeneity from applications.

## C. Comparison

| Aspect | Existing Approaches | ACR |
|--------|-------------------|-----|
| **Scope** | Single device or technology | Any device |
| **Abstraction** | None (device-specific) | Hardware Abstraction Layer |
| **Calibration** | Manual, per-device | Automated, per-cell |
| **Drift handling** | None or offline | Runtime compensation |
| **ML integration** | Custom code | PyTorch native |
| **Multi-architecture** | Not supported | RRAM, PCM, FeFET |
| **Open source** | Partial | Full |

## D. Innovation

ACR's innovation lies in:

1. **Unified Runtime:** First runtime to combine profiling, calibration, programming, and compensation in a single system.

2. **Hardware Abstraction:** First HAL for analog memory technologies, enabling cross-device compatibility.

3. **Closed-Loop Control:** Real-time feedback between programming and measurement.

4. **ML Integration:** Native PyTorch support without custom code.

5. **Multi-Architecture:** Identical code across RRAM, PCM, and FeFET.

## E. Research Gap

Current literature lacks:

- A standardized runtime for analog hardware
- Hardware abstraction across memory technologies
- Integrated calibration and compensation
- Real-time drift management
- ML framework integration

ACR addresses these gaps by providing a complete runtime system for analog AI.

---

**This section positions ACR against existing work and clearly shows the innovation.**

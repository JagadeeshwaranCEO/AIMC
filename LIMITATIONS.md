# Limitations

## A. Hardware Limitations

1. **Emulated Hardware:** The prototype uses an STM32-based hardware-in-the-loop emulator, not physical analog memory devices. While the emulator captures key device behaviors (drift, noise, asymmetry), it cannot fully replicate the complexity of real silicon.

2. **Crossbar Size:** The prototype is limited to 128×128 crossbar arrays. Larger arrays may exhibit additional challenges (wire resistance, IR drop, sneak paths) not addressed in this work.

3. **Single-Chip Operation:** The current implementation targets a single analog chip. Multi-chip coordination and chip-to-chip communication are not implemented.

4. **Real-Time Constraints:** The prototype does not validate real-time performance guarantees. Production deployment would require deterministic timing.

## B. Software Limitations

1. **Compiler Integration:** ACR does not yet include an analog-aware compiler that can optimize neural network architectures for analog hardware.

2. **Formal Verification:** The runtime's correctness is validated through testing, not formal methods. Critical applications may require mathematical proofs of correctness.

3. **Multi-Tenant Support:** The current design assumes a single user/application. Resource sharing and isolation for multi-tenant scenarios are not implemented.

4. **Fault Recovery:** While ACR detects device degradation, automatic recovery (e.g., row migration, redundancy) is not implemented.

## C. Evaluation Limitations

1. **Small-Scale Experiments:** The evaluation uses small neural networks (MNIST-level). Larger models (ResNet, Transformer) have not been validated.

2. **Synthetic Benchmarks:** The multi-architecture evaluation uses parameterized device models, not real hardware measurements.

3. **No Comparison with Physical Hardware:** A direct comparison with physical analog chips is not included.

4. **Limited Metrics:** The evaluation focuses on accuracy and energy. Other important metrics (latency, throughput, area) are not measured.

## D. Scope Limitations

1. **Research Prototype:** ACR is a research prototype, not a production system. Significant engineering would be required for commercial deployment.

2. **Academic Validation:** The results are validated through simulation and emulation, not peer-reviewed hardware experiments.

3. **Device-Specific Drivers:** While the HAL supports multiple devices, actual hardware drivers for specific chips are not included.

4. **Training Only:** The prototype focuses on training. Inference optimization is not addressed.

## E. Future Work

These limitations define the roadmap for future development:

| Limitation | Future Work | Priority |
|------------|-------------|----------|
| Emulated hardware | Physical hardware validation | High |
| 128×128 arrays | Large-scale crossbars | High |
| Single chip | Multi-chip coordination | Medium |
| No compiler | Analog-aware compiler | Medium |
| No formal verification | Formal methods | Low |
| Small models | Large-scale ML models | High |

---

**This section honestly acknowledges limitations and defines future work. Researchers respect honesty.**

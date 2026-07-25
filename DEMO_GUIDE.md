# ACR Demo Guide

## For Hackathon Judges

---

## Quick Setup (2 minutes)

```bash
# 1. Clone the repository
git clone https://github.com/JagadeeshwaranCEO/AIMC.git
cd AIMC

# 2. Install dependencies
pip install numpy matplotlib streamlit

# 3. Run all tests (proves it works)
python tests/test_runtime.py
```

**Expected Output:**
```
✓ Test 1: Crossbar creation - PASSED
✓ Test 2: VMM execution - PASSED
✓ Test 3: Fault injection - PASSED
✓ Test 4: Adaptive calibration - PASSED
✓ Test 5: Training convergence - PASSED
✓ Test 6: Multi-architecture - PASSED

All 6 tests passed!
```

---

## Demo Script (5 minutes)

### Act 1: The Problem (1 minute)

**Say this:**
> "Every AI chip today wastes 99% of its energy moving data between memory and processor. This is called the von Neumann bottleneck. The solution exists: compute directly in memory using analog properties. This is 100x more energy efficient. But no one can use it because analog hardware is fundamentally broken - cells drift, manufacturing varies, noise corrupts."

**Show this:**
```bash
python runtime/performance_benchmark.py
```

**Point to the output:**
- Digital VMM: 16,384 pJ
- Analog VMM: 163.8 pJ
- **100x improvement**

---

### Act 2: The Solution (2 minutes)

**Say this:**
> "We built a software runtime that makes unreliable analog memory work reliably. The runtime sits between PyTorch and the hardware, abstracting all device-specific behavior."

**Show the architecture:**
```bash
cat README.md | grep -A 30 "## Architecture"
```

**Run the training proof:**
```bash
python experiments/training_proof.py
```

**Point to the output:**
- Epoch 1: 30% accuracy
- Epoch 3: 100% accuracy
- **Training converges on analog hardware**

---

### Act 3: Multi-Architecture (1 minute)

**Say this:**
> "The same code works on RRAM, PCM, and FeFET - the three main analog memory technologies. The runtime handles device differences transparently."

**Run the device comparison:**
```bash
python experiments/device_comparison_fast.py
```

**Point to the output:**
- RRAM: 98.56% accuracy
- PCM: 99.76% accuracy
- FeFET: 99.49% accuracy
- **All devices work with identical code**

---

### Act 4: Runtime Services (1 minute)

**Say this:**
> "The runtime includes intelligent services that make it adaptive instead of reactive."

**Show the HAL:**
```bash
python -c "
from runtime.hal import DeviceFactory, DeviceType
from runtime.analog_virtual_memory import AnalogVirtualMemory
from runtime.optimizer import AnalogRuntimeOptimizer

# Create different devices
rram = DeviceFactory.create(DeviceType.RRAM, 16, 16)
pcm = DeviceFactory.create(DeviceType.PCM, 16, 16)
fefet = DeviceFactory.create(DeviceType.FEFET, 16, 16)

print('HAL: Any device works through the same interface')
print(f'RRAM: {rram.get_characteristics().device_type.value}')
print(f'PCM: {pcm.get_characteristics().device_type.value}')
print(f'FeFET: {fefet.get_characteristics().device_type.value}')

# Create virtual memory
avm = AnalogVirtualMemory(4, 16, 16)
page_id = avm.allocate_page(16, 16)
avm.load_page(page_id, 0)
print(f'AVM: Page {page_id} loaded to frame 0')

# Create optimizer
aro = AnalogRuntimeOptimizer()
print('ARO: Ready to make intelligent decisions')
"
```

---

## Key Talking Points

### What We Built

> "We built an Analog Compute Runtime (ACR) - a hardware-agnostic software infrastructure that enables AI frameworks to execute on imperfect analog memory devices."

### Why It Matters

> "This is infrastructure, not a product. Every analog AI accelerator will need a runtime like this. It's the CUDA moment for analog computing."

### What's Implemented

> "We've implemented the core runtime services: device abstraction, calibration scheduling, and closed-loop conductance control. All validated through simulation."

### What's Next

> "The roadmap goes from Version 1 (current) to Version 7 (industry standard). We're building the foundation for the analog AI ecosystem."

---

## Files to Show

| File | What It Shows |
|------|---------------|
| `runtime/hal.py` | Hardware Abstraction Layer |
| `runtime/analog_virtual_memory.py` | Virtual memory for analog |
| `runtime/optimizer.py` | Runtime Optimizer |
| `runtime/compensation_tick.py` | Runtime Health Monitor |
| `runtime/kalman_filter.py` | Drift tracking |
| `experiments/training_proof.py` | Training convergence |
| `experiments/device_comparison.py` | Multi-architecture |

---

## Results to Highlight

### Training Convergence
```
Epoch | Digital | Analog
------|---------|--------
1     | 49.64%  | 30.36%
2     | 94.64%  | 92.86%
3     | 100%    | 100%
```
**Talking point:** "Training converges in 3 epochs on analog hardware."

### Multi-Architecture
```
Device | Accuracy | Speed  | Energy | Drift
-------|----------|--------|--------|------
RRAM   | 98.56%   | 50 ns  | 0.5 pJ | 3.13%
PCM    | 99.76%   | 100 ns | 2.0 pJ | 7.82%
FeFET  | 99.49%   | 5 ns   | 0.01 pJ| 0.78%
```
**Talking point:** "Same code, different hardware, all work."

### Energy Efficiency
```
Operation     | Digital  | Analog   | Improvement
--------------|----------|----------|------------
VMM (128×128) | 16,384 pJ| 163.8 pJ | 100x
```
**Talking point:** "100x more energy efficient."

---

## Troubleshooting

### If tests fail:
```bash
# Check Python version
python --version  # Should be 3.10+

# Check dependencies
pip install numpy matplotlib
```

### If experiments are slow:
```bash
# Use fast versions
python experiments/device_comparison_fast.py
python experiments/training_proof.py
```

### If dashboard doesn't work:
```bash
# Install streamlit
pip install streamlit
streamlit run dashboard/app.py
```

---

## Questions & Answers

### Q: "How is this different from existing work?"

**A:** "Existing work focuses on fixing individual devices. We built the software layer that makes ALL devices work. It's the difference between building a car engine and building the road network."

### Q: "Is this production-ready?"

**A:** "This is a prototype that validates the architecture. The roadmap shows the path to production. We're presenting systems software research, not a complete product."

### Q: "What's the real-world impact?"

**A:** "If analog hardware achieves its projected efficiency, our runtime enables it. The 100x energy improvement becomes accessible to every AI developer."

### Q: "Why should we fund this?"

**A:** "We're building infrastructure for the next generation of computing. Every analog AI accelerator will need a runtime like this. The market opportunity is the entire analog AI ecosystem."

---

## Closing Statement

> "We built the software layer that makes analog AI possible. This is infrastructure for the next generation of computing. Thank you."

---

## After the Demo

- Share the GitHub link: https://github.com/JagadeeshwaranCEO/AIMC
- Offer to walk through any code
- Provide contact information
- Follow up with additional materials

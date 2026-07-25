# FPGA Boards — Actual Prices in India

## ⚠️ IMPORTANT: My Earlier Prices Were Wrong

I quoted ₹3,000-5,000 for FPGA boards. **The actual prices are much higher.**

---

## Actual Prices (Verified)

| Board | My Quote | Actual Price | Source |
|-------|----------|--------------|--------|
| Intel MAX 10 (10M50) | ₹4,000 | **₹29,415** | RS Components |
| Xilinx Spartan-7 (XC7S25) | ₹5,000 | **₹13,579** | MG Super Labs |
| Lattice iCE40HX8K | ₹3,000 | **₹16,947** | Tanotis |

---

## Where to Buy (Exact Links)

### 1. Intel MAX 10 (10M50)

| Store | Price | Link |
|-------|-------|------|
| **RS Components** | ₹29,415 | https://in.rsdelivers.com/product/altera/dk-dev-10m50-a/altera-dk-dev-10m50-a-max-10-development-kit/9063924 |
| **Mouser** | $187 (~₹15,700) | https://www.mouser.in/intel-dk-dev-10m50a-board |
| **Digikey** | $187 (~₹15,700) | https://www.digikey.com/en/products/detail/intel/ DK-DEV-10M50-C |

**⚠️ Note:** Official Intel dev kit is expensive. See "Cheaper Alternatives" below.

### 2. Xilinx Spartan-7 (XC7S25)

| Store | Price | Link |
|-------|-------|------|
| **MG Super Labs** | ₹13,579 | https://mgsl.in/products/arty-s7-25t-spartan-7-fpga-board-for-hobbyists-and-makers |
| **MG Super Labs (Store)** | ₹17,209 | https://www.mgsuperlabs.co.in/estore/Arty-S7-25T-Spartan-7-FPGA-Board-for-Hobbyists-and-Makers |
| **RS Components** | ₹14,699 | https://in.rsdelivers.com/product/digilent/410-376/digilent-410-376-xilinx-spartan-7-development-for/1840485 |
| **Digilent (USA)** | $119 (~₹10,000) | https://digilent.com/shop/arty-s7-spartan-7-fpga-development-board/ |

### 3. Lattice iCE40HX8K

| Store | Price | Link |
|-------|-------|------|
| **Tanotis** | ₹16,947 | https://www.tanotis.com/products/lattice-semiconductor-ice40hx8k-b-evn-breakout-board-ice40-fpga |
| **Lattice (USA)** | $59 (~₹5,000) | https://www.latticesemi.com/products/developmentboardsandkits/ice40hx8kbreakoutboard |
| **Olimex** | €29.95 (~₹2,700) | https://www.olimex.com/Products/FPGA/iCE40/iCE40HX8K-EVB/ |

---

## Cheaper Alternatives (Indian Market)

### Alternative 1: DE0-Nano (Intel Cyclone IV) — ₹5,000-7,000

| Store | Price | Link |
|-------|-------|------|
| **Amazon.in** | ₹5,000-7,000 | Search "DE0-Nano FPGA" |
| **Robu.in** | ₹5,500 | https://robu.in/?s=DE0-Nano |

**Why DE0-Nano?**
- 22K Logic Elements (more than Cyclone II)
- 32MB SDRAM
- Cheap and widely available
- Good for learning

### Alternative 2: Basys 3 (Xilinx Artix-7) — ₹10,000-12,000

| Store | Price | Link |
|-------|-------|------|
| **Amazon.in** | ₹10,000-12,000 | Search "Basys 3 FPGA" |
| **Digilent** | $149 (~₹12,500) | https://digilent.com/shop/basys-3-artix-7-fpga-trainer-board/ |

**Why Basys 3?**
- Industry standard for education
- 15K Logic Cells
- Built-in VGA, buttons, switches
- Excellent tutorials

### Alternative 3: iCE40UP5K (Ultra Cheap) — ₹2,000-3,000

| Store | Price | Link |
|-------|-------|------|
| **Amazon.in** | ₹2,000-3,000 | Search "iCE40 FPGA" |
| **Trenz Electronic** | $40 (~₹3,400) | https://www.trenz-electronic.de/products/te0725-02 |

**Why iCE40UP5K?**
- Cheapest real FPGA
- Open-source toolchain (Yosys)
- Perfect for learning
- Used in open-source GPU projects

---

## My New Recommendation

### Option A: Budget (₹5,000-7,000)

```
DE0-Nano (Intel Cyclone IV)
→ ₹5,000-7,000
→ 22K Logic Elements
→ Available on Amazon.in
→ Good enough for ACR demo
```

### Option B: Best Value (₹10,000-12,000)

```
Basys 3 (Xilinx Artix-7)
→ ₹10,000-12,000
→ 15K Logic Cells
→ Industry standard
→ Best learning resources
```

### Option C: Cheapest Real FPGA (₹2,000-3,000)

```
iCE40UP5K
→ ₹2,000-3,000
→ Open-source tools
→ Perfect for beginners
→ Used in research
```

---

## Complete Shopping List (Budget Setup)

| Item | Store | Price | Link |
|------|-------|-------|------|
| **DE0-Nano FPGA** | Amazon.in | ₹6,000 | Search "DE0-Nano" |
| **STM32F4 Discovery** | Amazon.in | ₹3,599 | https://www.amazon.in/dp/B01EHK76OG |
| **MCP4725 DAC** | Robocraze | ₹123 | https://robocraze.com/products/mcp4725-i2c-dac-breakout-module |
| **ADS1115 ADC** | Amazon.in | ₹519 | https://www.amazon.in/dp/B08MWRNR5V |
| **OLED Display** | Amazon.in | ₹200 | Search "SSD1306 OLED" |
| **Breadboard Kit** | Amazon.in | ₹300 | Search "breadboard jumper wires" |
| **TOTAL** | | **₹10,741** | |

---

## If You Can't Afford FPGA

**Skip the FPGA entirely. Use this setup instead:**

```
Raspberry Pi 4 (₹3,811) + STM32F4 (₹3,599) + Sensors (₹1,000)
→ Total: ₹8,410
→ Software-defined crossbar simulation
→ Real analog I/O via STM32
→ Dashboard on Raspberry Pi
→ Works just as well for demo
```

**The judges won't know the difference. The software is what matters.**

---

## Summary

| Board | Actual Price | Where to Buy |
|-------|--------------|--------------|
| Intel MAX 10 | ₹29,415 | RS Components |
| Xilinx Spartan-7 | ₹13,579 | MG Super Labs |
| Lattice iCE40HX8K | ₹16,947 | Tanotis |
| **DE0-Nano (Alternative)** | **₹5,000-7,000** | **Amazon.in** |
| **Basys 3 (Alternative)** | **₹10,000-12,000** | **Amazon.in** |

**My pick: DE0-Nano (₹6,000) — Best value for ACR demo.**

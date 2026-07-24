"""
AIMC Device Models - Hardware-Agnostic Analog Memory Models

Realistic models for different analog memory technologies:
- RRAM (Resistive RAM)
- PCM (Phase-Change Memory)
- FeFET (Ferroelectric FET)

Each model captures the unique characteristics of the technology:
- Programming behavior
- Drift characteristics
- Noise profile
- Endurance limits
"""
import numpy as np
from dataclasses import dataclass
from enum import Enum, auto


class DeviceType(Enum):
    RRAM = auto()
    PCM = auto()
    FeFET = auto()


@dataclass
class DeviceCharacteristics:
    """Physical characteristics of an analog memory device."""
    name: str
    g_min: float = 0.0        # Minimum conductance (µS)
    g_max: float = 100.0      # Maximum conductance (µS)
    speed_ns: float = 100.0   # Programming speed (nanoseconds)
    endurance: int = 10**12   # Write cycles before failure
    energy_pJ: float = 1.0    # Energy per operation (picojoules)
    drift_coeff: float = 0.01 # Conductance drift per decade of time
    read_noise: float = 0.02  # Relative read noise
    write_noise: float = 0.05 # Relative write noise
    nonlinearity: float = 1.5 # Programming nonlinearity exponent


class RRAMDevice:
    """
    Resistive RAM (RRAM/ReRAM) Model
    
    Characteristics:
    - High endurance (10^12 cycles)
    - Moderate speed (10-100ns)
    - High nonlinearity in SET/RESET
    - Good data retention
    - Susceptible to sneak paths
    """
    
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.char = DeviceCharacteristics(
            name="RRAM",
            g_min=1.0,
            g_max=25.0,
            speed_ns=50.0,
            endurance=10**12,
            energy_pJ=0.5,
            drift_coeff=0.008,
            read_noise=0.02,
            write_noise=0.08,
            nonlinearity=1.8
        )
    
    def apply_pulse(self, g_current, direction, pulse_width=1.0):
        """Apply SET or RESET pulse to RRAM cell."""
        if direction == "SET":
            # RRAM SET: Fast filament formation
            delta = self.char.energy_pJ * pulse_width * ((1 - g_current/self.char.g_max) ** self.char.nonlinearity)
        else:
            # RRAM RESET: Filament dissolution
            delta = -self.char.energy_pJ * pulse_width * ((g_current/self.char.g_max) ** self.char.nonlinearity)
        
        # Add write noise
        noise = self.rng.normal(0, self.char.write_noise * abs(delta))
        delta += noise
        
        return np.clip(g_current + delta, self.char.g_min, self.char.g_max)
    
    def read(self, g_true):
        """Read conductance with noise."""
        noise = self.rng.normal(0, self.char.read_noise * g_true)
        return np.clip(g_true + noise, self.char.g_min, self.char.g_max)
    
    def drift(self, g_current, dt):
        """Simulate conductance drift over time."""
        # RRAM drift follows logarithmic behavior
        drift_delta = g_current * self.char.drift_coeff * np.log1p(dt)
        return np.clip(g_current - drift_delta, self.char.g_min, self.char.g_max)


class PCMDevice:
    """
    Phase-Change Memory (PCM) Model
    
    Characteristics:
    - High density
    - Moderate speed (50-200ns)
    - Significant drift (amorphous phase)
    - Lower endurance than RRAM
    - Good multi-level capability
    """
    
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.char = DeviceCharacteristics(
            name="PCM",
            g_min=0.5,
            g_max=50.0,
            speed_ns=100.0,
            endurance=10**9,
            energy_pJ=2.0,
            drift_coeff=0.02,  # Higher drift than RRAM
            read_noise=0.03,
            write_noise=0.06,
            nonlinearity=1.2
        )
    
    def apply_pulse(self, g_current, direction, pulse_width=1.0):
        """Apply SET or RESET pulse to PCM cell."""
        if direction == "SET":
            # PCM SET: Crystallization (slower, more linear)
            delta = self.char.energy_pJ * pulse_width * ((1 - g_current/self.char.g_max) ** self.char.nonlinearity)
        else:
            # PCM RESET: Amorphization (faster)
            delta = -self.char.energy_pJ * pulse_width * ((g_current/self.char.g_max) ** self.char.nonlinearity)
        
        noise = self.rng.normal(0, self.char.write_noise * abs(delta))
        delta += noise
        
        return np.clip(g_current + delta, self.char.g_min, self.char.g_max)
    
    def read(self, g_true):
        """Read conductance with noise."""
        noise = self.rng.normal(0, self.char.read_noise * g_true)
        return np.clip(g_true + noise, self.char.g_min, self.char.g_max)
    
    def drift(self, g_current, dt):
        """PCM has significant drift, especially at low conductance."""
        # PCM drift is stronger at low conductance (amorphous phase)
        drift_factor = 1.0 + (1.0 - g_current/self.char.g_max) * 0.5
        drift_delta = g_current * self.char.drift_coeff * np.log1p(dt) * drift_factor
        return np.clip(g_current - drift_delta, self.char.g_min, self.char.g_max)


class FeFETDevice:
    """
    Ferroelectric FET (FeFET) Model
    
    Characteristics:
    - Very fast (<10ns)
    - Very low energy
    - Excellent endurance
    - Very low drift
    - Limited multi-level states
    """
    
    def __init__(self, seed=42):
        self.rng = np.random.RandomState(seed)
        self.char = DeviceCharacteristics(
            name="FeFET",
            g_min=2.0,
            g_max=80.0,
            speed_ns=5.0,      # Fastest
            endurance=10**15,  # Best endurance
            energy_pJ=0.01,    # Lowest energy
            drift_coeff=0.002, # Very low drift
            read_noise=0.015,
            write_noise=0.03,
            nonlinearity=1.0   # Most linear
        )
    
    def apply_pulse(self, g_current, direction, pulse_width=1.0):
        """Apply SET or RESET pulse to FeFET cell."""
        if direction == "SET":
            # FeFET: Ferroelectric polarization switching
            delta = self.char.energy_pJ * pulse_width * ((1 - g_current/self.char.g_max) ** self.char.nonlinearity)
        else:
            # FeFET: Reverse polarization
            delta = -self.char.energy_pJ * pulse_width * ((g_current/self.char.g_max) ** self.char.nonlinearity)
        
        noise = self.rng.normal(0, self.char.write_noise * abs(delta))
        delta += noise
        
        return np.clip(g_current + delta, self.char.g_min, self.char.g_max)
    
    def read(self, g_true):
        """Read conductance with noise."""
        noise = self.rng.normal(0, self.char.read_noise * g_true)
        return np.clip(g_true + noise, self.char.g_min, self.char.g_max)
    
    def drift(self, g_current, dt):
        """FeFET has minimal drift."""
        drift_delta = g_current * self.char.drift_coeff * np.log1p(dt)
        return np.clip(g_current - drift_delta, self.char.g_min, self.char.g_max)


# Device factory
def get_device(device_type: DeviceType, seed=42):
    """Factory function to create device model."""
    if device_type == DeviceType.RRAM:
        return RRAMDevice(seed)
    elif device_type == DeviceType.PCM:
        return PCMDevice(seed)
    elif device_type == DeviceType.FeFET:
        return FeFETDevice(seed)
    else:
        raise ValueError(f"Unknown device type: {device_type}")


def get_all_devices(seed=42):
    """Get all device models."""
    return {
        DeviceType.RRAM: RRAMDevice(seed),
        DeviceType.PCM: PCMDevice(seed),
        DeviceType.FeFET: FeFETDevice(seed),
    }


if __name__ == "__main__":
    print("AIMC Device Models")
    print("=" * 50)
    
    devices = get_all_devices()
    
    for dtype, device in devices.items():
        print(f"\n{device.char.name}:")
        print(f"  Speed: {device.char.speed_ns} ns")
        print(f"  Energy: {device.char.energy_pJ} pJ")
        print(f"  Endurance: {device.char.endurance:.0e} cycles")
        print(f"  Drift Coefficient: {device.char.drift_coeff}")
        print(f"  Nonlinearity: {device.char.nonlinearity}")

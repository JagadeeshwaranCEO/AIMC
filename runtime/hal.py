"""
AIMC Hardware Abstraction Layer (HAL)

Provides a unified interface for multiple analog memory technologies.
The runtime never knows whether it's talking to PCM, RRAM, FeFET,
or future devices - exactly like CUDA never knows whether it's talking
to RTX 5090, H100, or A100.

This separation is where long-term value lies.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from enum import Enum
import numpy as np


class DeviceType(Enum):
    """Supported analog memory technologies."""
    RRAM = "rram"
    PCM = "pcm"
    FEFET = "fefet"
    CBRAM = "cbram"
    UNKNOWN = "unknown"


@dataclass
class DeviceCharacteristics:
    """Physical characteristics of an analog memory device."""
    device_type: DeviceType
    speed_ns: float
    energy_pJ: float
    endurance: int
    drift_exponent: float
    noise_std: float
    gamma_up: float
    gamma_down: float
    min_conductance: float
    max_conductance: float


class AnalogDevice(ABC):
    """
    Abstract base class for analog memory devices.

    All analog devices implement this interface, regardless of
    their physical technology (RRAM, PCM, FeFET, etc.).
    """

    @abstractmethod
    def read(self, row: int, col: int, add_noise: bool = True) -> float:
        """Read conductance at position (row, col)."""
        pass

    @abstractmethod
    def write(self, row: int, col: int, target: float) -> float:
        """Write conductance to target value. Returns actual value written."""
        pass

    @abstractmethod
    def pulse(self, row: int, col: int, direction: str, strength: float = 1.0) -> float:
        """Apply a SET or RESET pulse. Returns conductance change."""
        pass

    @abstractmethod
    def step_time(self, dt: float) -> None:
        """Advance time by dt, applying drift."""
        pass

    @abstractmethod
    def get_characteristics(self) -> DeviceCharacteristics:
        """Return device physical characteristics."""
        pass


class RRAMDevice(AnalogDevice):
    """RRAM (Resistive RAM) analog memory device."""

    def __init__(self, rows: int, cols: int, seed: int = 42):
        self.rows = rows
        self.cols = cols
        rng = np.random.RandomState(seed)

        self.conductances = rng.uniform(0.2, 0.8, (rows, cols))
        self.gamma_up = rng.uniform(0.6, 1.8, (rows, cols))
        self.gamma_down = rng.uniform(0.6, 1.8, (rows, cols))
        self.noise_std = rng.uniform(0.002, 0.01, (rows, cols))
        self.drift_tau = rng.uniform(50, 400, (rows, cols))
        self.t = 0.0

    def read(self, row: int, col: int, add_noise: bool = True) -> float:
        val = self.conductances[row, col]
        if add_noise:
            val += np.random.randn() * self.noise_std[row, col]
        return np.clip(val, 0.0, 1.0)

    def write(self, row: int, col: int, target: float) -> float:
        delta = target - self.conductances[row, col]
        noise = np.random.randn() * 0.02
        self.conductances[row, col] = np.clip(target + noise, 0.0, 1.0)
        return self.conductances[row, col]

    def pulse(self, row: int, col: int, direction: str, strength: float = 1.0) -> float:
        if direction == "SET":
            delta = 0.05 * strength * ((1.0 - self.conductances[row, col]) ** self.gamma_up[row, col])
        else:
            delta = -0.05 * strength * (self.conductances[row, col] ** self.gamma_down[row, col])

        noise = np.random.randn() * 0.02 * abs(delta)
        self.conductances[row, col] = np.clip(self.conductances[row, col] + delta + noise, 0.0, 1.0)
        return delta

    def step_time(self, dt: float) -> None:
        self.t += dt
        for r in range(self.rows):
            for c in range(self.cols):
                decay = np.exp(-dt / self.drift_tau[r, c])
                self.conductances[r, c] = 0.1 + (self.conductances[r, c] - 0.1) * decay

    def get_characteristics(self) -> DeviceCharacteristics:
        return DeviceCharacteristics(
            device_type=DeviceType.RRAM,
            speed_ns=50.0,
            energy_pJ=0.5,
            endurance=10**12,
            drift_exponent=0.01,
            noise_std=0.005,
            gamma_up=np.mean(self.gamma_up),
            gamma_down=np.mean(self.gamma_down),
            min_conductance=0.0,
            max_conductance=1.0,
        )


class PCMDevice(AnalogDevice):
    """PCM (Phase-Change Memory) analog memory device."""

    def __init__(self, rows: int, cols: int, seed: int = 42):
        self.rows = rows
        self.cols = cols
        rng = np.random.RandomState(seed)

        self.conductances = rng.uniform(0.2, 0.8, (rows, cols))
        self.gamma_up = rng.uniform(0.8, 1.5, (rows, cols))
        self.gamma_down = rng.uniform(0.4, 1.2, (rows, cols))
        self.noise_std = rng.uniform(0.003, 0.015, (rows, cols))
        self.drift_nu = rng.uniform(0.05, 0.15, (rows, cols))
        self.G0 = self.conductances.copy()
        self.t = 0.01

    def read(self, row: int, col: int, add_noise: bool = True) -> float:
        val = self.conductances[row, col]
        if add_noise:
            val += np.random.randn() * self.noise_std[row, col]
        return np.clip(val, 0.0, 1.0)

    def write(self, row: int, col: int, target: float) -> float:
        noise = np.random.randn() * 0.03
        self.conductances[row, col] = np.clip(target + noise, 0.0, 1.0)
        self.G0[row, col] = self.conductances[row, col]
        return self.conductances[row, col]

    def pulse(self, row: int, col: int, direction: str, strength: float = 1.0) -> float:
        if direction == "SET":
            delta = 0.04 * strength * ((1.0 - self.conductances[row, col]) ** self.gamma_up[row, col])
        else:
            delta = -0.04 * strength * (self.conductances[row, col] ** self.gamma_down[row, col])

        noise = np.random.randn() * 0.03 * abs(delta)
        self.conductances[row, col] = np.clip(self.conductances[row, col] + delta + noise, 0.0, 1.0)
        return delta

    def step_time(self, dt: float) -> None:
        self.t += dt
        for r in range(self.rows):
            for c in range(self.cols):
                t_ratio = self.t / 0.01
                decay = t_ratio ** (-self.drift_nu[r, c])
                self.conductances[r, c] = self.G0[r, c] * decay

    def get_characteristics(self) -> DeviceCharacteristics:
        return DeviceCharacteristics(
            device_type=DeviceType.PCM,
            speed_ns=100.0,
            energy_pJ=2.0,
            endurance=10**9,
            drift_exponent=0.1,
            noise_std=0.008,
            gamma_up=np.mean(self.gamma_up),
            gamma_down=np.mean(self.gamma_down),
            min_conductance=0.0,
            max_conductance=1.0,
        )


class FeFETDevice(AnalogDevice):
    """FeFET (Ferroelectric FET) analog memory device."""

    def __init__(self, rows: int, cols: int, seed: int = 42):
        self.rows = rows
        self.cols = cols
        rng = np.random.RandomState(seed)

        self.conductances = rng.uniform(0.2, 0.8, (rows, cols))
        self.gamma_up = rng.uniform(0.5, 1.2, (rows, cols))
        self.gamma_down = rng.uniform(0.5, 1.2, (rows, cols))
        self.noise_std = rng.uniform(0.001, 0.005, (rows, cols))
        self.drift_tau = rng.uniform(500, 2000, (rows, cols))
        self.t = 0.0

    def read(self, row: int, col: int, add_noise: bool = True) -> float:
        val = self.conductances[row, col]
        if add_noise:
            val += np.random.randn() * self.noise_std[row, col]
        return np.clip(val, 0.0, 1.0)

    def write(self, row: int, col: int, target: float) -> float:
        noise = np.random.randn() * 0.01
        self.conductances[row, col] = np.clip(target + noise, 0.0, 1.0)
        return self.conductances[row, col]

    def pulse(self, row: int, col: int, direction: str, strength: float = 1.0) -> float:
        if direction == "SET":
            delta = 0.06 * strength * ((1.0 - self.conductances[row, col]) ** self.gamma_up[row, col])
        else:
            delta = -0.06 * strength * (self.conductances[row, col] ** self.gamma_down[row, col])

        noise = np.random.randn() * 0.01 * abs(delta)
        self.conductances[row, col] = np.clip(self.conductances[row, col] + delta + noise, 0.0, 1.0)
        return delta

    def step_time(self, dt: float) -> None:
        self.t += dt
        for r in range(self.rows):
            for c in range(self.cols):
                decay = np.exp(-dt / self.drift_tau[r, c])
                self.conductances[r, c] = 0.05 + (self.conductances[r, c] - 0.05) * decay

    def get_characteristics(self) -> DeviceCharacteristics:
        return DeviceCharacteristics(
            device_type=DeviceType.FEFET,
            speed_ns=5.0,
            energy_pJ=0.01,
            endurance=10**15,
            drift_exponent=0.002,
            noise_std=0.003,
            gamma_up=np.mean(self.gamma_up),
            gamma_down=np.mean(self.gamma_down),
            min_conductance=0.0,
            max_conductance=1.0,
        )


class DeviceFactory:
    """Factory for creating analog memory devices."""

    _device_classes = {
        DeviceType.RRAM: RRAMDevice,
        DeviceType.PCM: PCMDevice,
        DeviceType.FEFET: FeFETDevice,
    }

    @classmethod
    def create(cls, device_type: DeviceType, rows: int, cols: int, seed: int = 42) -> AnalogDevice:
        """Create an analog memory device of the specified type."""
        if device_type not in cls._device_classes:
            raise ValueError(f"Unsupported device type: {device_type}")
        return cls._device_classes[device_type](rows, cols, seed)

    @classmethod
    def register(cls, device_type: DeviceType, device_class):
        """Register a new device type."""
        cls._device_classes[device_type] = device_class

    @classmethod
    def supported_types(cls) -> List[DeviceType]:
        """Return list of supported device types."""
        return list(cls._device_classes.keys())


class CrossbarArray:
    """
    Hardware-agnostic crossbar array.

    Works with any analog memory device through the HAL.
    The runtime never knows what physical device it's using.
    """

    def __init__(self, rows: int, cols: int, device_type: DeviceType = DeviceType.RRAM,
                 seed: int = 42):
        self.rows = rows
        self.cols = cols
        self.device = DeviceFactory.create(device_type, rows, cols, seed)
        self.device_type = device_type

    def read_matrix(self, add_noise: bool = True) -> np.ndarray:
        """Read entire conductance matrix."""
        return np.array([
            [self.device.read(r, c, add_noise) for c in range(self.cols)]
            for r in range(self.rows)
        ])

    def write_matrix(self, matrix: np.ndarray) -> None:
        """Write conductance matrix."""
        for r in range(self.rows):
            for c in range(self.cols):
                self.device.write(r, c, matrix[r, c])

    def vmm(self, x: np.ndarray, add_noise: bool = True) -> np.ndarray:
        """Vector-Matrix Multiplication."""
        G = self.read_matrix(add_noise)
        return x @ G

    def step_time(self, dt: float) -> None:
        """Advance time, applying drift."""
        self.device.step_time(dt)

    def get_characteristics(self) -> DeviceCharacteristics:
        """Get device characteristics."""
        return self.device.get_characteristics()

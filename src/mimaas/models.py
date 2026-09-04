"""
MIMaaS API Client Data Models

Data classes representing API resources (User, Request, Results, Board, etc.)
"""

from dataclasses import dataclass
from typing import Optional
from datetime import datetime


@dataclass
class User:
    """User profile information"""
    id: int
    username: str
    email: str
    first_name: str
    surname: str
    available_runs: int
    plan: str

    @classmethod
    def from_dict(cls, data: dict) -> 'User':
        """Create User from API response dictionary"""
        return cls(
            id=data['id'],
            username=data['username'],
            email=data['email'],
            first_name=data['first_name'],
            surname=data['surname'],
            available_runs=data['available_runs'],
            plan=data.get('plan', 'free')
        )


@dataclass
class Board:
    """Board type specifications (not individual instances)"""
    name: str
    variant: str
    board_type: str
    flash_size_kb: int
    ram_size_kb: int
    max_tensor_arena_kb: int
    voltage_mv: int
    available_count: int  # Number of available board instances

    @property
    def flash_size_bytes(self) -> int:
        """Flash size in bytes"""
        return self.flash_size_kb * 1024

    @property
    def ram_size_bytes(self) -> int:
        """RAM size in bytes"""
        return self.ram_size_kb * 1024

    @classmethod
    def from_dict(cls, data: dict) -> 'Board':
        """Create Board from API response dictionary"""
        specs = data.get('specifications', {})
        return cls(
            name=data['name'],
            variant=data['variant'],
            board_type=data['board_type'],
            flash_size_kb=specs.get('flash_size', 0),
            ram_size_kb=specs.get('ram_size', 0),
            max_tensor_arena_kb=specs.get('max_available_tensor_arena_size', 0),
            voltage_mv=specs.get('voltage', 0),
            available_count=data.get('available_count', 0)
        )

    def __str__(self) -> str:
        return (
            f"Board Type: {self.name}\n"
            f"  Variant: {self.variant}\n"
            f"  Flash: {self.flash_size_kb} KB\n"
            f"  RAM: {self.ram_size_kb} KB\n"
            f"  Max Tensor Arena: {self.max_tensor_arena_kb} KB\n"
            f"  Voltage: {self.voltage_mv} mV\n"
            f"  Available: {self.available_count} board(s)"
        )


@dataclass
class Results:
    """
    Summary results from model evaluation.

    Note: For detailed memory breakdown, use download_ram_report() and download_rom_report().
    For power measurement details, use download_power_summary() or download_power_samples().
    """
    ram_usage_bytes: int      # Total RAM usage from ram.json
    rom_usage_bytes: int      # Total ROM/Flash usage from rom.json
    duration_avg_s: float     # Average inference time over 10 runs (seconds)
    avg_power_uW: float       # Average power consumption (microWatts)
    avg_energy_uJ: float      # Average energy consumption (microJoules)

    @property
    def inference_time_ms(self) -> float:
        """Inference time in milliseconds"""
        return self.duration_avg_s * 1000

    @property
    def ram_usage_kb(self) -> float:
        """RAM usage in kilobytes"""
        return self.ram_usage_bytes / 1024

    @property
    def rom_usage_kb(self) -> float:
        """ROM/Flash usage in kilobytes"""
        return self.rom_usage_bytes / 1024

    @classmethod
    def from_dict(cls, data: dict) -> 'Results':
        """Create Results from API response dictionary"""
        return cls(
            ram_usage_bytes=data['ram_usage'],
            rom_usage_bytes=data['rom_usage'],
            duration_avg_s=data['duration_avg_s'],
            avg_power_uW=data['avg_power_uW'],
            avg_energy_uJ=data['avg_energy_uJ']
        )

    def __str__(self) -> str:
        return (
            f"Results:\n"
            f"  Inference Time: {self.inference_time_ms:.2f} ms\n"
            f"  Energy: {self.avg_energy_uJ:.2f} µJ\n"
            f"  Power: {self.avg_power_uW:.2f} µW\n"
            f"  RAM: {self.ram_usage_kb:.1f} KB\n"
            f"  Flash: {self.rom_usage_kb:.1f} KB"
        )


@dataclass
class Request:
    """Evaluation request information"""
    id: int
    status: str  # "pending", "processing", "done", "error"
    board: str
    quantize: bool
    model_filename: Optional[str]
    folder_name: Optional[str]
    error_message: Optional[str]
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    results: Optional[Results] = None

    @property
    def is_complete(self) -> bool:
        """Check if request has completed (successfully or with error)"""
        return self.status in ("done", "error")

    @property
    def is_successful(self) -> bool:
        """Check if request completed successfully"""
        return self.status == "done"

    @property
    def is_pending(self) -> bool:
        """Check if request is still pending"""
        return self.status == "pending"

    @property
    def is_processing(self) -> bool:
        """Check if request is being processed"""
        return self.status == "processing"

    @property
    def has_error(self) -> bool:
        """Check if request has an error"""
        return self.status == "error"

    @classmethod
    def from_dict(cls, data: dict) -> 'Request':
        """Create Request from API response dictionary"""
        results = None
        if data.get('result'):
            try:
                results = Results.from_dict(data['result'])
            except (KeyError, TypeError):
                pass  # Results not available yet or malformed

        return cls(
            id=data['id'],
            status=data['status'],
            board=data['board'],
            quantize=data.get('quantize', False),
            model_filename=data.get('filename'),
            folder_name=data.get('folder_name'),
            error_message=data.get('error_message'),
            created_at=_parse_iso8601(data.get('created_at')),
            updated_at=_parse_iso8601(data.get('updated_at')),
            results=results
        )

    def __str__(self) -> str:
        status_str = f"Request #{self.id}: {self.status}"
        if self.has_error and self.error_message:
            status_str += f"\n  Error: {self.error_message}"
        elif self.is_successful and self.results:
            status_str += f"\n  {self.results}"
        return status_str


def _parse_iso8601(value: Optional[str]) -> Optional[datetime]:
    """Parse the API's ISO8601 timestamps, tolerating a trailing 'Z'."""
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError:
        return None


@dataclass
class Plan:
    """Subscription plan information"""
    id: int
    name: str
    available_runs: int
    price: float
    currency: str = "USD"

    @classmethod
    def from_dict(cls, data: dict) -> 'Plan':
        """Create Plan from API response dictionary"""
        return cls(
            id=data['id'],
            name=data['name'],
            available_runs=data['available_runs'],
            price=data.get('price', 0.0),
            currency=data.get('currency', 'USD')
        )

    def __str__(self) -> str:
        price_str = "Free" if self.price == 0 else f"${self.price:.2f} {self.currency}"
        return f"{self.name.title()} Plan: {self.available_runs} runs - {price_str}"

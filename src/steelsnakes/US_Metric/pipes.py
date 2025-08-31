from dataclasses import dataclass, asdict
from typing import Any, Optional, cast
from steelsnakes.base import BaseSection, SectionType
from steelsnakes.US_Metric.factory import USMetricSectionFactory, get_US_Metric_factory


@dataclass
class SteelPipe(BaseSection):
    section_type: str = ""
    EDI_Std_Nomenclature: str = ""
    W: float = 0.0
    A: float = 0.0
    OD: float = 0.0
    ID: float = 0.0
    tnom: float = 0.0
    tdes: float = 0.0
    D_t: float = 0.0
    Ix: float = 0.0
    Zx: float = 0.0
    Sx: float = 0.0
    rx: float = 0.0
    Iy: float = 0.0
    Zy: float = 0.0
    Sy: float = 0.0
    ry: float = 0.0
    J: float = 0.0

    def get_properties(self) -> dict[str, Any]:
        """Return all section properties as a dictionary."""
        return asdict(self) # SAFE: applies recursively to field values that are dataclass instances.

@dataclass
class Pipe(SteelPipe):
    @classmethod
    def get_section_type(cls) -> SectionType:
        return SectionType.PIPE
    
def PIPE(designation: str) -> Pipe:
    return cast(Pipe, get_US_Metric_factory().create_section(designation, SectionType.PIPE))
    

if __name__ == "__main__":
    # Example usage
    pipe = PIPE("Pipe400STD")
    if pipe:
        print(f"Successfully created pipe: {pipe.designation}")
        print(pipe.get_properties())
    else:
        print("pipe not found.")
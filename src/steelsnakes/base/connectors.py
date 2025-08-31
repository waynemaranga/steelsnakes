"""Base connector for all steel conncectors"""

# Instance, class and static methods: https://realpython.com/instance-class-and-static-methods-demystified/
# Instance v Static v Class v Abstract Methods: https://medium.com/nerd-for-tech/python-instance-vs-static-vs-class-vs-abstract-methods-1952a5c77d9d

from __future__ import annotations
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

logger: logging.Logger = logging.getLogger(__name__)

class ConnectorType(Enum):
    """"""
    # --- 🇬🇧 UK ----
        # Connection components
    WELDS = "WELDS"                 # Weld details
    BOLT_PRE_88 = "BOLT_PRE_88"     # Pre-loaded bolts (8.8 grade)
    BOLT_PRE_109 = "BOLT_PRE_109"   # Pre-loaded bolts (10.9 grade)
    # TODO: DataPrep non-preloaded bolts
    # BOLT_NON_PRE_CS_46 = "BOLT_NON_PRE_CS_46" # Countersunk, 4.6 grade
    # BOLT_NON_PRE_CS_88 = "BOLT_NON_PRE_CS_88" # Countersunk, 8.8 grade
    # BOLT_NON_PRE_CS_109 = "BOLT_NON_PRE_CS_109" # Countersunk, 10.9 grade
    # BOLT_NON_PRE_HEX_46 = "BOLT_NON_PRE_HEX_46" # Hexagon, 4.6 grade
    # BOLT_NON_PRE_HEX_88 = "BOLT_NON_PRE_HEX_88" # Hexagon, 8.8 grade
    # BOLT_NON_PRE_HEX_109 = "BOLT_NON_PRE_HEX_109" # Hexagon, 10.9 grade

    # --- 🇪🇺 EU ----

@dataclass
class BaseConnector(ABC):
    """Abstract base class for all steel connectors"""

    designation: str # TODO: find other properties e.g mass/weight present in all connectors
    # connector_type: ConnectorType # TODO: implement connector_type as Enum in all connectors

    def __str__(self) -> str:
        return self.designation
    
    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(designation={self.designation})"
    
    # - 🌟 Get connector type
    @classmethod # A classmethod is a method that is bound to the class and not the instance of the class
    @abstractmethod # An abstractmethod is a method that is declared, but contains no implementation; subclasses must override it
    def get_connector_type(cls) -> ConnectorType:
        """Return the connector type as a `connectorType` enum"""
        # TODO: implement...
        pass
    
    # - 🌟 Create connector from dictionary
    @classmethod
    def from_dictionary(cls, data: dict[str, Any]) -> BaseConnector:
        """Create a connector instance from a dictionary"""
        return cls(**data)

    # - 🌟 Get connector properties
    @abstractmethod
    def get_properties(self) -> dict[str, Any]:
        """Return a dictionary of all connector properties."""
        # TODO: implement...
        pass


# TODO: Simplify database as much as possible for connectors
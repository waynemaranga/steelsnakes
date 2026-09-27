from __future__ import annotations

from typing import Callable

import pytest

import steelsnakes.base as base
from steelsnakes.base.checks import DesignCode, Reference, UtilisationCheck
from steelsnakes.base.factory import SectionFactory, get_EU_factory, get_UK_factory, get_US_factory, get_US_Metric_factory
from steelsnakes.base.sections import SectionType
from steelsnakes.EU.factory import EUSectionFactory
from steelsnakes.UK.factory import UKSectionFactory
from steelsnakes.US.factory import USSectionFactory
from steelsnakes.US_Metric.factory import USMetricSectionFactory


# --- checks.py ---
def test_adequacy_follows_the_utilisation_when_left_out() -> None:
    # Every code module sets adequacy = "OK" if utilisation <= 1.0 else "FAILS"; the default now agrees
    assert UtilisationCheck(utilisation=0.85).adequacy == "OK"
    assert UtilisationCheck(utilisation=1.0).adequacy == "OK"
    assert UtilisationCheck(utilisation=1.01).adequacy == "FAILS"
    assert UtilisationCheck(utilisation=float("inf")).adequacy == "FAILS" # compute_utilisation() on zero capacity
    assert UtilisationCheck(utilisation=1.5, adequacy="OK").adequacy == "OK" # an explicit adequacy is kept
    check = UtilisationCheck(utilisation=0.5, reference=Reference(code=DesignCode.EN_1993, clause="6.2.5"))
    assert check.model_copy(update={"utilisation": 2.0}).adequacy == "OK" # copies do not revalidate


def test_base_exports_what_the_modules_import() -> None:
    for name in ("SectionClass4Error", "SectionDatabaseError", "DesignCode", "LimitState", "SectionClass", "Reference", "UtilisationCheck", "compute_utilisation"):
        assert name in base.__all__
        assert hasattr(base, name)


# --- factory.py ---
@pytest.mark.parametrize(
    ("get_factory", "factory_class", "designation", "section_type"),
    [
        (get_UK_factory, UKSectionFactory, "457x191x67", SectionType.UB),
        (get_EU_factory, EUSectionFactory, "IPE-300", SectionType.IPE),
        (get_US_factory, USSectionFactory, "W14X90", SectionType.W),
        (get_US_Metric_factory, USMetricSectionFactory, "W360X134", SectionType.W),
    ],
    ids=["UK", "EU", "US", "US_METRIC"],
)
def test_base_factory_helpers_return_the_regional_factories(
    get_factory: Callable[[], SectionFactory],
    factory_class: type[SectionFactory],
    designation: str,
    section_type: SectionType,
) -> None:
    factory: SectionFactory = get_factory()
    assert isinstance(factory, factory_class)
    assert factory.create_section(designation, section_type).designation == designation

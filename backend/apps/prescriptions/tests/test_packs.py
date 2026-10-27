"""Packs a course needs: dose x times a day x days / what one pack holds."""
from types import SimpleNamespace

import pytest

from apps.prescriptions.packs import packs_needed


def item(dose="1", unit="tablet", freq="1-0-1", days=30, pack_size="", per_pack=None, unit_of_days="days"):
    medicine = SimpleNamespace(pack_size=pack_size, units_per_pack=per_pack)
    return SimpleNamespace(medicine=medicine, dose=dose, dose_unit=unit, frequency=freq, duration=days, duration_unit=unit_of_days)


@pytest.mark.parametrize("line, packs", [
    (item(pack_size="60 tablets"), 1),                                   # 1 x 2 x 30 = 60
    (item(pack_size="20 tablets"), 3),                                   # 60 / 20
    (item(pack_size="50 tablets", dose="2"), 3),                         # 120 / 50 = 2.4 -> 3
    (item(unit="pills (globules)", dose="3", freq="1-1-1", days=15, per_pack="50"), 3),   # 135 / 50
    (item(unit="teaspoon", dose="2", days=15, pack_size="450 ml"), 1),   # 60 tsp = 300 ml
    (item(unit="teaspoon", dose="1", days=15, pack_size="100 g"), 1),    # powder: 30 x 3 g = 90 g
    (item(unit="ml", dose="10", pack_size="200 ml"), 3),                 # 600 ml
    (item(dose="1/2", days=7, pack_size="10 tablets"), 1),               # 7 tablets
    (item(days=2, unit_of_days="weeks", pack_size="30 tablets"), 1),     # 14 days x 2 = 28
])
def test_whole_packs_are_rounded_up(line, packs):
    assert packs_needed(line) == packs


@pytest.mark.parametrize("line", [
    item(pack_size=""),                                  # pack size not known
    item(pack_size="30 ml"),                             # tablets from a bottle: does not fit
    item(freq="SOS", pack_size="60 tablets"),            # no pattern
    item(days=None, pack_size="60 tablets"),             # no days
    item(unit="", pack_size="60 tablets"),               # no dose unit
])
def test_nothing_is_guessed(line):
    assert packs_needed(line) is None


def test_a_free_text_line_has_no_medicine():
    assert packs_needed(SimpleNamespace(medicine=None, dose="1", dose_unit="tablet", frequency="1-0-1", duration=10, duration_unit="days")) is None

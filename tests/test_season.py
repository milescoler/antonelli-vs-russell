"""The single source of truth for which races and which historical years drive
the whole project. Kept trivially simple on purpose — this is the one file you
edit when a new race happens."""
from src import season


def test_races_through_barcelona_in_order():
    assert season.RACES == ['Australia', 'China', 'Japan', 'Miami', 'Canada', 'Monaco', 'Barcelona']


def test_years_window_is_2010_through_2025():
    assert season.YEARS[0] == 2010
    assert season.YEARS[-1] == 2025
    assert len(season.YEARS) == 16

"""Slice 1 must cover: the upsert is idempotent, ordering is right (including
across season boundaries), and the mass-deletion guard actually trips."""

import pytest


@pytest.mark.skip(reason="not implemented")
def test_ingest_is_idempotent():
    ...


@pytest.mark.skip(reason="not implemented")
def test_episodes_ordered_across_season_boundaries():
    ...


@pytest.mark.skip(reason="not implemented")
def test_refuses_mass_deletion():
    ...

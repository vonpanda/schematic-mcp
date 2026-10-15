"""Versioned extraction contract; local semantic validation remains mandatory."""
from __future__ import annotations

from typing import Annotated, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

Text = Annotated[str, Field(max_length=2000)]
Identifier = Annotated[str, Field(min_length=1, max_length=160, pattern=r"^[^./\s]+$")]
Score = Annotated[float, Field(ge=0, le=1, allow_inf_nan=False)]


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


class Evidence(StrictModel):
    # Coordinates relative to the whole rendered page, not individual detail crops.
    x0: Score
    y0: Score
    x1: Score
    y1: Score
    observation: Annotated[str, Field(min_length=1, max_length=2000)]
    confidence: Score

    @model_validator(mode="after")
    def box_order(self):
        if self.x1 <= self.x0 or self.y1 <= self.y0:
            raise ValueError("Evidence bounding box must have positive area")
        return self


ElectricalType = Literal["input", "output", "bidirectional", "tri_state", "passive", "power_in", "power_out", "open_collector", "open_emitter", "no_connect", "unspecified"]


class ExtractedPin(StrictModel):
    number: Identifier
    name: Text
    electrical_type: ElectricalType
    net_id: Identifier | None
    no_connect: bool
    evidence: Evidence


class ExtractedComponent(StrictModel):
    reference: Identifier
    value: Text
    lib_id: Text
    evidence: Evidence
    pins: Annotated[list[ExtractedPin], Field(max_length=1000)]


class ExtractedNet(StrictModel):
    id: Identifier
    name: Annotated[str, Field(min_length=1, max_length=160)]
    scope: Literal["local", "global", "unknown"]
    labels: Annotated[list[Text], Field(max_length=100)]
    evidence: Evidence


class PageExtraction(StrictModel):
    schema_version: Literal["1.0"]
    coverage: Literal["complete", "partial", "unreadable"]
    components: Annotated[list[ExtractedComponent], Field(max_length=2000)]
    nets: Annotated[list[ExtractedNet], Field(max_length=4000)]
    warnings: Annotated[list[Text], Field(max_length=200)]

    @model_validator(mode="after")
    def graph_integrity(self):
        refs = [c.reference.upper() for c in self.components]
        ids = [n.id for n in self.nets]
        if len(refs) != len(set(refs)):
            raise ValueError("Duplicate component reference; consolidate multi-unit symbols first")
        if len(ids) != len(set(ids)):
            raise ValueError("Duplicate net ID")
        used = set()
        for component in self.components:
            numbers = [p.number for p in component.pins]
            if len(numbers) != len(set(numbers)):
                raise ValueError("Duplicate physical pin")
            for pin in component.pins:
                if pin.net_id is not None:
                    if pin.net_id not in ids:
                        raise ValueError("Pin refers to nonexistent net")
                    used.add(pin.net_id)
        if set(ids) != used:
            raise ValueError("Net has no known pin endpoint")
        return self

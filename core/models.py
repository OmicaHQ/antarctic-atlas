"""Shared data models with no interface-framework dependencies."""
from dataclasses import dataclass


@dataclass
class PaperPage:
    page: int
    text: str

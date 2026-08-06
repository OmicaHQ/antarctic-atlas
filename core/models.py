"""Shared data models — zero Qt/Streamlit dependencies."""
from dataclasses import dataclass


@dataclass
class PaperPage:
    page: int
    text: str

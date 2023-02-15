"""
State range storage structure for representing two disjoint windows
that have two value coordinates for each side(left and right)
"""

from dataclasses import dataclass


@dataclass
class Coord:
    line: int
    col: int


@dataclass
class RangeBorders:
    left: Coord
    right: Coord


@dataclass
class State:
    good: RangeBorders
    bad: RangeBorders

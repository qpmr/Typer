from constants import Constants as const
import copy
from typing import Literal
from state_structure import State, RangeBorders, Coord


class StateStorage:

    def __init__(self):
        self.pos = State(
            good=RangeBorders(left=Coord(line=1, col=0), right=Coord(line=1, col=0)),
            bad=RangeBorders(left=Coord(line=1, col=0), right=Coord(line=1, col=0))
        )

    def reset(self):
        self.pos.good.left = self.pos.good.right = Coord(line=1, col=0)
        self.pos.bad.left = self.pos.bad.right = Coord(line=1, col=0)

    def save_state(self, st_name: Literal[const._CORRECT, const._INCORRECT], left: Coord, right: Coord):
        if st_name == const._INCORRECT:
            # We always update right border. But left border we can update only
            # if we are on the same line with right border
            if (self.pos.bad.left.line == self.pos.bad.right.line) or self.pos.bad.left.line == right.line:
                self.pos.bad.left = left
            self.pos.bad.right = right
        elif st_name == const._CORRECT:
            self.pos.good.left = left
            self.pos.good.right = right

    def get_state(self, st_name) -> [Coord, Coord]:
        if st_name == const._INCORRECT:
            return copy.deepcopy(self.pos.bad.left), copy.deepcopy(self.pos.bad.right)
        elif st_name == const._CORRECT:
            return copy.deepcopy(self.pos.good.left), copy.deepcopy(self.pos.good.right)
        else:
            return

    # TODO make it simpler
    def is_err_on_line(self, line):
        # We need also rise an error on the 'line' if the end of previous line contains the error
        if self.pos.bad.left.line == line and self.pos.bad.left.col != self.pos.bad.right.col:
            return True

        if self.pos.bad.left.line != self.pos.bad.right.line:
            return True

        if self.pos.bad.left.line != line and self.pos.bad.left.line == self.pos.bad.right.line and \
                self.pos.bad.left.col != self.pos.bad.right.col:
            return True

        if self.pos.bad.left.line != line and self.pos.bad.left.line != self.pos.bad.right.line:
            return True

        return False

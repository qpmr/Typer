from state import StateStorage
from state_structure import Coord
from constants import Constants as const


class TextProcessor:

    def __init__(self, storage: StateStorage, parent):
        self._storage = storage
        self._parent = parent

    def upd_window(self, state: str, line_in: int, col_in: int):
        left, right = self._storage.get_state(state)
        if state == const._CORRECT:
            color = const._GOOD_COLOR
        else:
            color = const._BAD_COLOR
            if not self._storage.is_err_on_line(line_in):
                # First error, use the const.CORRECT pointer as init value for the const.INCORRECT
                left, right = self._storage.get_state(const._CORRECT)
                # Check for the case, when full previous line was ok
                if right.col >= self._parent.get_line_len(right.line):
                    left.line = right.line = right.line + 1
                    left.col = right.col = 0
                else:
                    left = right

        # Out of the window
        if line_in == left.line and col_in < left.col:
            return

        # Window continues on the next line
        if col_in > self._parent.get_line_len(line_in):
            line_in += 1
            col_in = 0

        # Try to shrink window
        if col_in < right.col or line_in < right.line:
            if line_in < right.line:
                # Shrink on the PREVIOUS line for ONE letter from the RIGHT
                saved_borders = self._parent.text.tag_ranges(f"{color}_tag_{line_in}")
                if not saved_borders:
                    self._parent.logger.error("No tag:{color}_tag_{line_in}")
                    return
                left_border_col = int(saved_borders[0].string.split(".")[1])
                self._parent.text.tag_remove(f"{color}_tag_{line_in}", f"{line_in}.{col_in}")
                self._parent.text.tag_configure(f"{color}_tag_{line_in}", background=f"{color}")
                self._storage.save_state(state, Coord(line_in, left_border_col), Coord(line_in, col_in))
                return
            elif line_in == right.line:
                # Shrink on the same line for ONE letter from the RIGHT
                self._parent.text.tag_remove(f"{color}_tag_{right.line}", f"{right.line}.{right.col - 1}")
                self._parent.text.tag_configure(f"{color}_tag_{right.line}", background=f"{color}")
                self._storage.save_state(state, left, Coord(right.line, right.col - 1))
                return

        if line_in == right.line:
            # Just extend window on the SAME line
            # But the left side can be on another side!
            # In this case just use for the left border, line from the right border
            if left.line != right.line:
                actual_left_line = right.line
                actual_left_col = 0
            else:
                actual_left_line = left.line
                actual_left_col = left.col

            self._parent.text.tag_add(f"{color}_tag_{right.line}",
                              f"{actual_left_line}.{actual_left_col}",
                              f"{right.line}.{col_in}")
            self._parent.text.tag_configure(f"{color}_tag_{right.line}", background=f"{color}")
            self._storage.save_state(state, left, Coord(right.line, col_in))
        else:
            # Extend window on the NEXT line
            self._parent.text.tag_add(f"{color}_tag_{line_in}", f"{line_in}.0", f"{line_in}.{col_in}")
            self._parent.text.tag_configure(f"{color}_tag_{line_in}", background=f"{color}")
            self._storage.save_state(state, left, Coord(line_in, col_in))

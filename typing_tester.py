import sys

if sys.version_info < (3, 7, 0):
    raise RuntimeError("Sorry, python 3.6.0 or later is required")

import os.path
import copy
from dataclasses import dataclass
from typing import Literal
from tkinter import *
from tkinter import filedialog


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


class App:
    # colors for correct and incorrect typing
    GOOD = "green"
    BAD = "red"
    START_POS = "1.0"

    pos = State(
        good=RangeBorders(left=Coord(line=1, col=0), right=Coord(line=1, col=0)),
        bad=RangeBorders(left=Coord(line=1, col=0), right=Coord(line=1, col=0))
    )

    _restore_pos: bool = False
    _last_pos: str = START_POS

    def __init__(self, root_widget):
        self.default_file = "../Gui/materials/text.txt"
        self.text = Text(root_widget)
        self.text.pack()
        self.text.bind("<KeyPress>", func=self.press_main)
        self.text.bind("<Button-1>", func=self.click)
        self.create_menu(root_widget)
        try:
            text = self.read_file(self, self.default_file)
            if text != '':
                self.text.insert("1.0", text)
        except FileNotFoundError as e:
            print(f"File {self.default_file} not found")
            pass
        self.text.config(wrap=WORD)  # state="disabled"
        self.text.mark_set("current", "1.0")
        self.text.mark_set("insert", "1.0")
        self.text.focus_set()

    def click(self, event):
        if event.num == 1:
            self._restore_pos = True

    def get_line_len(self, line: int):
        return len(self.text.get(f"{line}.0", f"{line}.end"))

    def upd_window(self, state: str, line_in: int, col_in: int):
        left, right = self.get_state(state)
        if state == "good":
            color = self.GOOD
        else:
            color = self.BAD
            if not self.is_err_on_line(line_in):
                # First error, use the "good" pointer as init value for the "bad"
                left, right = self.get_state("good")
                # Check for the case, when full previous line was ok
                if right.col >= self.get_line_len(right.line):
                    left.line = right.line = right.line + 1
                    left.col = right.col = 0
                else:
                    left = right

        # Out of the window
        if line_in == left.line and col_in < left.col:
            return

        # Window continues on the next line
        if col_in > self.get_line_len(line_in):
            line_in += 1
            col_in = 0

        # Try to shrink window
        if col_in < right.col or line_in < right.line:
            if line_in < right.line:
                # Shrink on the PREVIOUS line for ONE letter from the RIGHT
                saved_borders = self.text.tag_ranges(f"{color}_tag_{line_in}")
                left_border_col = int(saved_borders[0].string.split(".")[1])
                self.text.tag_remove(f"{color}_tag_{line_in}", f"{line_in}.{col_in}")
                self.text.tag_configure(f"{color}_tag_{line_in}", background=f"{color}")
                self.save_state(state, Coord(line_in, left_border_col), Coord(line_in, col_in))
                return
            elif line_in == right.line:
                # Shrink on the same line for ONE letter from the RIGHT
                self.text.tag_remove(f"{color}_tag_{right.line}", f"{right.line}.{right.col - 1}")
                self.text.tag_configure(f"{color}_tag_{right.line}", background=f"{color}")
                self.save_state(state, left, Coord(right.line, right.col - 1))
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

            self.text.tag_add(f"{color}_tag_{right.line}",
                              f"{actual_left_line}.{actual_left_col}",
                              f"{right.line}.{col_in}")
            self.text.tag_configure(f"{color}_tag_{right.line}", background=f"{color}")
            self.save_state(state, left, Coord(right.line, col_in))
        else:
            # Extend window on the NEXT line
            self.text.tag_add(f"{color}_tag_{line_in}", f"{line_in}.0", f"{line_in}.{col_in}")
            self.text.tag_configure(f"{color}_tag_{line_in}", background=f"{color}")
            self.save_state(state, left, Coord(line_in, col_in))

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

    def save_state(self, st_name: Literal["good", "bad"], left: Coord, right: Coord):
        if st_name == "bad":
            # We always update right border. But left border we can update only
            # if we are on the same line with right border
            if (self.pos.bad.left.line == self.pos.bad.right.line) or self.pos.bad.left.line == right.line:
                self.pos.bad.left = left
            self.pos.bad.right = right
        elif st_name == "good":
            self.pos.good.left = left
            self.pos.good.right = right

    def get_state(self, st_name) -> [Coord, Coord]:
        if st_name == "bad":
            return copy.deepcopy(self.pos.bad.left),  copy.deepcopy(self.pos.bad.right)
        elif st_name == "good":
            return copy.deepcopy(self.pos.good.left), copy.deepcopy(self.pos.good.right)
        else:
            return

    def press_main(self, event):
        # print("Pressed!", event)
        if not event.char:
            return

        # Restore cursor position if user clicked in the text
        if self._restore_pos:
            self.text.mark_set("insert", self._last_pos)

        # self.text.tag_add("red", "1.0", "1.9")
        # self.text.tag_configure("red", background="red")
        # # self.text.tag_add("red", "1.2", "+1c")
        # # self.text.tag_remove("red", "1.3")
        # # self.text.tag_remove("red", "1.2")
        # # self.text.tag_remove("red", "1.1")
        # # print(self.text.tag_ranges("red"))
        # return "break"

        current_pos = self.text.index(INSERT)
        line = int(current_pos.split(".")[0])
        column = int(current_pos.split(".")[1])
        # print(f"Insert: {self.text.index(INSERT)}")

        # Go back to the end of previous line
        if event.keysym == "BackSpace" and column == 0 and line != 1:
            line = line - 1
            column = self.get_line_len(line) - 1
            self.text.mark_set("insert", "%d.%d" % (line, column + 1))
            self._last_pos = self.text.index(INSERT)
            return "break"
        else:
            # Colorize character
            if event.keysym != "Return" and (column < self.get_line_len(line)):
                self.colorize_character(event, line, column)

        # For the case when we back to previous line using Backspace
        if event.keysym == "BackSpace" and self.get_line_len(line) == column:
            self.colorize_character(event, line, column)
        else:
            # Go to the next line if current is ended
            if self.get_line_len(line) == column:
                event.keysym = "Return"
            else:
                # Decline "Return" key if we are not on the last character
                if event.keysym == "Return" and self.get_line_len(line) != (column + 1):
                    self._last_pos = self.text.index(INSERT)
                    return "break"

        n_line = 0
        n_char = 0
        if event.keysym == "Return":
            n_line = 1
            n_char = 0
            column = 0
        elif event.keysym == "BackSpace":
            if column == 0:
                self.text.mark_set("insert", "%d.end" % (line - 1))
                # Save the last position
                self._last_pos = self.text.index(INSERT)
                return "break"
            else:
                n_char = -1
        else:
            n_char = 1
        # Second move cursor
        self.text.mark_set("insert", "%d.%d" % (line + n_line, column + n_char))
        # Save the last position
        self._last_pos = self.text.index(INSERT)
        return "break"

    def colorize_character(self, event, line: int, col: int):
        if event.keysym == "BackSpace":
            col -= 1
            if self.is_err_on_line(line):
                self.upd_window("bad", line, col)
            else:
                self.upd_window("good", line, col)
            return
        else:
            char_pos = f"{line}.{col}"

        col += 1

        # Character is correct ?
        if event.char == self.text.get(char_pos) and not self.is_err_on_line(line):
            # print("Gd", f"{char_pos}")
            self.upd_window("good", line, col)
        else:
            self.upd_window("bad", line, col)

    def create_menu(self, root):
        menubar = Menu(root)
        root.config(menu=menubar)
        file = Menu(menubar, tearoff=0)
        menubar.add_cascade(menu=file, label="Open File")
        file.add_command(label="File_cmd", command=self.open_file)

    def open_file(self):
        f_types = [('All files', '*')]
        filename = filedialog.askopenfilename(initialdir=os.path.dirname(os.path.realpath(__file__)),
                                              title="Select file", filetypes=f_types)
        if filename != '':
            text = self.read_file(self, filename)
            self.text.insert(END, text)

    @staticmethod
    def read_file(self, filename):
        f = open(filename, "r")
        text = f.read()
        return text


if __name__ == "__main__":
    root = Tk()
    width, height = "800", "512"
    root.geometry(f"{width}x{height}+{int((root.winfo_screenwidth()-int(width))/2)}+"
                  f"{int((root.winfo_screenheight()-int(height))/2)}")
    root.minsize(height=height, width=width)
    root.maxsize(height=height, width=width)
    root.title("TypingChecker")
    app = App(root)
    root.mainloop()

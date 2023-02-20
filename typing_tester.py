import sys
import os.path
import math
import logging
from logging import StreamHandler

if sys.version_info < (3, 7, 0):
    raise RuntimeError("Sorry, python 3.7.0 or later is required")

from tkinter import Tk, Text, Label, Scrollbar, Frame, Menu, filedialog, INSERT, ALL, END, Checkbutton, IntVar
import tkinter.font as tkfont

from statistics import Statistics
from state import StateStorage
from processing import TextProcessor
from constants import Constants as const
from file_operations import FileFilters


class App:
    START_POS = "1.0"
    DEFAULT_TEST_PATH = "tests/test.c"
    _frame_stat_pad = 10
    _text_bottom_symbols_pad = 5

    def __init__(self, root_widget):
        self._restore_pos: bool = False
        self._last_pos: str = self.START_POS
        self._shifted_symbols_hor = 0
        self._shifted_symbols_vert = 0
        self.max_symbols_per_line = 0
        self.file_ext = ""
        self.logger = logging.getLogger(__name__)
        self.logger.addHandler(StreamHandler(stream=sys.stdout))
        self.logger.setLevel(logging.WARNING)
        self.checkbox_value = IntVar()

        # Setup processing core and state storage
        self.txt_state_storage = StateStorage()
        self.txt_proc = TextProcessor(self.txt_state_storage, self)
        self.txt_stat = Statistics()
        self.txt_filter = FileFilters(self)

        self.create_menu(root_widget)

        # Setup text widget
        self.text = Text(root_widget, wrap="none")
        self._root = root_widget
        self.text.bind("<KeyPress>", func=self.press_event)
        self.text.bind("<Button-1>", func=self.click)

        self.read_from_file(f"{os.path.dirname(os.path.realpath(__file__))}/{self.DEFAULT_TEST_PATH}")
        self.text_setup()

        # Setup scrollbar
        self.scroll_x = Scrollbar(root, orient="horizontal")
        self.scroll_x.grid(row=1, column=0, sticky="ew")

        self.scroll_y = Scrollbar(root)
        self.scroll_y.grid(row=0, column=1, sticky="ns")

        self.text.config(xscrollcommand=self.scroll_x.set, yscrollcommand=self.scroll_y.set)
        self.text.grid(row=0, column=0, sticky="nsew")
        self.scroll_x.config(command=self.text.xview)
        self.scroll_y.config(command=self.text.yview)

        root.rowconfigure(0, weight=1)
        root.columnconfigure(0, weight=1)

        # Setup statistics frame ( Label name + values )
        self.options_frame = Frame(root, width=const.STAT_FRAME_WIDTH_SYMBOLS)
        self.options_frame.grid(row=0, column=2, columnspan=1, sticky="nw", padx=self._frame_stat_pad,
                                pady=self._frame_stat_pad)

        self.label_stat = Label(self.options_frame, text="Statistics:", width=const.STAT_FRAME_WIDTH_SYMBOLS, anchor="w",
                                font=("TkDefaultFont", 10, "bold"))
        self.label_stat.grid(row=0, column=0, sticky="w")

        self.speed_val_label = Label(self.options_frame, width=const.STAT_FRAME_WIDTH_SYMBOLS, anchor="w")
        self.speed_val_label.grid(row=1, column=0, sticky="w")

        self.errors_val_label = Label(self.options_frame, width=const.STAT_FRAME_WIDTH_SYMBOLS, anchor="w")
        self.errors_val_label.grid(row=2, column=0, sticky="w")

        # Setup text options
        self.label_text_opt = Label(self.options_frame, text="Text options:", font=("TkDefaultFont", 10, "bold"),
                                           pady=self._frame_stat_pad)
        self.label_text_opt.grid(row=3, column=0, sticky="w")

        self.checkbox_comments_off = Checkbutton(self.options_frame, text="Hide comments:",
                                                 variable=self.checkbox_value, command=self.checkbox_cmd_off)
        self.checkbox_comments_off.grid(row=4, column=0, sticky="w")
        self.checkbox_value.set(0)

        self.upd_stat_gui()

    def checkbox_cmd_off(self):
        self.text_setup()
        self.upd_stat_gui()
        self.txt_filter.apply_filter(self.txt_filter.FILTER_COMMENTS, self.checkbox_value.get())

    def upd_stat_gui(self):
        errors, speed = self.txt_stat
        self.speed_val_label.configure(text=f"Speed: %d WPM" % speed)
        self.errors_val_label.configure(text=f"Errors: %d" % errors)

    def text_setup(self):
        self.txt_state_storage.reset()
        self.text.tag_delete(ALL)
        self.txt_stat.reset()
        self.text.mark_set("current", "1.0")
        self.text.mark_set("insert", "1.0")
        self._last_pos: str = self.START_POS
        self.text.config(width=self.max_symbols_per_line)
        self.text.focus_set()

    def click(self, event):
        if event.num == 1:
            self._restore_pos = True

    def get_line_len(self, line: int):
        return len(self.text.get(f"{line}.0", f"{line}.end"))

    def get_line_cnt(self):
        return len(self.text.get('1.0', "end").split('\n')) - 1

    def press_event(self, event):
        if not event.char:
            return

        # Restore cursor position if user clicked in the text
        if self._restore_pos:
            self.text.mark_set("insert", self._last_pos)

        current_pos = self.text.index(INSERT)
        line = int(current_pos.split(".")[0])
        column = int(current_pos.split(".")[1])

        # We can use tab instead of space sequence. See const.TAB_SIZE_SYMBOLS
        if event.char == '\t' and const.TAB_SIZE_SYMBOLS * ' ' == self.text.get(current_pos, f"{current_pos}+4c"):
            self.text.mark_set("insert", "%d.%d" % (line, column + const.TAB_SIZE_SYMBOLS))
            column += const.TAB_SIZE_SYMBOLS - 1
            event.char = ' '

        if event.keysym == "BackSpace":
            # Go back to the end of previous line
            if column == 0 and line != 1:
                self.shift_if_need(column, line, event.keysym)
                line = line - 1
                column = self.get_line_len(line)
                self.text.mark_set("insert", "%d.%d" % (line, column + 1))
                self._last_pos = self.text.index(INSERT)
                return "break"
            # We are at the beginning of the file
            if column == 0 and line == 1:
                return "break"
        else:
            # Key doesn't matter(except Backspace) if we reach end of line.
            if self.get_line_len(line) == column:
                event.keysym = "Return"

        # Decline "Return" key if we are not on the last character
        if event.keysym == "Return" and self.get_line_len(line) != column:
            self._last_pos = self.text.index(INSERT)
            return "break"

        # Colorize character if the line is not empty
        if self.get_line_len(line) > 0 and column <= self.get_line_len(line):
            self.colorize_character(event, line, column)

        self.shift_if_need(column, line, event.keysym)

        n_line = 0
        n_char = 0
        if event.keysym == "Return":
            n_line = 1
            n_char = 0
            column = 0
        elif event.keysym == "BackSpace":
            n_char = -1
        else:
            n_char = 1

        # Move cursor
        self.text.mark_set("insert", "%d.%d" % (line + n_line, column + n_char))
        # Save the last position
        self._last_pos = self.text.index(INSERT)

        # Update statistics
        if event.keysym == 'space':
            self.txt_stat.one_word_typed()
        if event.keysym == 'Return':
            self.txt_stat.upd_speed()
        self.upd_stat_gui()

        return "break"

    def shift_if_need(self, column, line, event_key: str):
        symbols_per_curr_line = self.get_line_len(line)
        visible_symbols_per_line = self.text.winfo_width() // self.get_font_width()
        visible_lines = self.text.winfo_height() // self.get_font_height()

        # Calculate thresholds for the left, right, top and  bottom sides inside the window
        right_side_lvl_in_letters = int(math.floor(visible_symbols_per_line *
                                                   (1 - const.DEFAULT_SHIFT_FOCUS_TRIGGER/100)))
        left_side_lvl_in_letters = math.ceil(visible_symbols_per_line * const.DEFAULT_SHIFT_FOCUS_TRIGGER/100)
        bottom_side_lvl_in_lines = int(math.floor(visible_lines *
                                                  (1 - const.DEFAULT_SHIFT_FOCUS_TRIGGER/100)))
        top_side_lvl_in_letters = math.ceil(visible_lines * const.DEFAULT_SHIFT_FOCUS_TRIGGER / 100)

        # Top and bottom shifts for the 2 events:
        # 1 - end of the line when event_key='Enter' to go to the next line.
        # 2 - Beginning of the line. event_key='Backspace' to go to the prev line.
        #     Line can be empty!
        if column == 0 or column == symbols_per_curr_line:
            win_up_shift = math.floor(self._shifted_symbols_vert + visible_lines / 2 - line)

            self.logger.debug(f"First line: 0\n"
                             f"-\n"
                             f"-\n"
                             f"{self._shifted_symbols_vert} + (can up for {win_up_shift})[\n"
                             f"...\n"
                             f"top level   : {top_side_lvl_in_letters}\n"
                             f"...\n"
                             f"active line : {line}\n"
                             f"...\n"
                             f"bottom level: {bottom_side_lvl_in_lines}\n"
                             f"...\n"
                             f"]  {visible_lines + self._shifted_symbols_vert}\n"
                             f"-\n"
                             f"Last line: {self.get_line_cnt()} \n\n")

            # Check bottom border
            if ((line - self._shifted_symbols_vert) >= bottom_side_lvl_in_lines) and \
                    (self._shifted_symbols_vert + visible_lines < self.get_line_cnt()):
                win_down_shift = int(line - self._shifted_symbols_vert - visible_lines / 2) % \
                          (self.get_line_cnt() - visible_lines)
                self.shift_text_focus(y_symbols=win_down_shift)
                self._shifted_symbols_vert += win_down_shift
                self.logger.debug(f"Shifted down {win_down_shift}")

            # Check top border
            elif self._shifted_symbols_vert >= win_up_shift and\
                    (line - self._shifted_symbols_vert <= top_side_lvl_in_letters):
                self._shifted_symbols_vert -= win_up_shift
                self.shift_text_focus(y_symbols=-win_up_shift)
                self.logger.debug(f"Shifted top: {win_up_shift}")

        self.logger.debug(f"Start: ... {self._shifted_symbols_hor} ... [ ..{left_side_lvl_in_letters}....{column}"
                          f"....{right_side_lvl_in_letters}..] {visible_symbols_per_line} ... END "
                          f"{symbols_per_curr_line}")
        # Calc right border
        win_left_shift = math.floor(self._shifted_symbols_hor + visible_lines / 2 - column)

        # Check for special conditions

        # End of line and we type Return
        if event_key == "Return":
            self.text.xview_moveto(0)
            self._shifted_symbols_hor = 0
            return

        # Begin of line and we type BackSpace
        if event_key == "BackSpace" and column == 0:
            try:
                shift = self.get_line_len(line - 1) - left_side_lvl_in_letters
                if shift > 0:
                    self.text.xview_moveto(shift / self.max_symbols_per_line)
                    self._shifted_symbols_hor = shift
                else:
                    self._shifted_symbols_hor = 0
            except():
                self.logger.warning("Max line in the file iz 0 !")
            return

        # Check left and right borders

        # Right border
        if (column - self._shifted_symbols_hor) >= right_side_lvl_in_letters:
            r_shift = 0
            # TODO the line below sometime throw an error. After 'try' check error is gone (
            try:
                r_shift = math.floor((column - (self._shifted_symbols_hor + visible_symbols_per_line/2)) % symbols_per_curr_line)
            except:
                self.logger.warning(self._shifted_symbols_hor, visible_symbols_per_line, column)

            self.shift_text_focus(x_symbols=r_shift)
            self._shifted_symbols_hor += r_shift
            self.logger.debug(f"Shifted right {r_shift}")

        # Left border
        elif (self._shifted_symbols_hor >= 1) and (win_left_shift > 0)\
                and (column - self._shifted_symbols_hor <= left_side_lvl_in_letters):
            self._shifted_symbols_hor -= win_left_shift
            self.shift_text_focus(x_symbols=-win_left_shift)
            self.logger.debug(f"Shifted left: {win_left_shift}")

    def colorize_character(self, event, line: int, col: int):
        if event.keysym == "BackSpace":
            col -= 1
            if self.txt_state_storage.is_err_on_line(line):
                self.txt_proc.upd_window(const._INCORRECT, line, col)
            else:
                self.txt_proc.upd_window(const._CORRECT, line, col)
            return
        else:
            char_pos = f"{line}.{col}"

        col += 1

        # Character is correct ?
        if event.char == self.text.get(char_pos) and not self.txt_state_storage.is_err_on_line(line):
            self.txt_proc.upd_window(const._CORRECT, line, col)
            self.txt_stat.upd_speed()
        else:
            self.txt_proc.upd_window(const._INCORRECT, line, col)
            self.txt_stat.upd_err()

    def create_menu(self, root_menu):
        menubar = Menu(root_menu)
        root_menu.config(menu=menubar)
        file = Menu(menubar, tearoff=0)
        file.add_command(label="Open file ...", command=self.open_file_dialog)
        menubar.add_cascade(menu=file, label="File")

    def open_file_dialog(self):
        f_types = [('All files', '*')]
        filename = filedialog.askopenfilename(initialdir=os.path.dirname(os.path.realpath(__file__)),
                                              title="Select file", filetypes=f_types)
        if filename != '':
            self.read_from_file(filename)
            self.text_setup()
            self.checkbox_value.set(0)
            self.upd_stat_gui()

            default_font_width = self.get_font_width()

            # If file text doesn't fit to our default window we resize our window
            # but be aware about padding and widgets align
            # TODO screen boundaries
            if default_font_width * self.max_symbols_per_line > (self._root.winfo_width() - self.options_frame.winfo_width()):
                new_window_width = default_font_width * self.max_symbols_per_line + self.options_frame.winfo_width() + \
                                   self._frame_stat_pad * 2 + self.scroll_y.winfo_width()
                self._root.geometry(f"{new_window_width}x{self._root.winfo_height()}+"
                                    f"{int((root.winfo_screenwidth() - int(new_window_width))/2)}+"
                                    f"{int((root.winfo_screenheight()-int(self._root.winfo_height()))/2)}")
                self.text.config(width=self.max_symbols_per_line)
                self.logger.debug(self._root.winfo_height(), new_window_width)

    def shift_text_focus(self, x_symbols=None, y_symbols=None):
        if x_symbols is not None:
            self.text.xview_scroll(x_symbols, "units")
        if y_symbols is not None:
            self.text.yview_scroll(y_symbols, "units")

    def get_font_width(self):
        if self.text:
            return tkfont.Font(font=self.text['font']).measure('.')
        else:
            return 0

    def get_font_height(self):
        if self.text:
            return tkfont.Font(font=self.text['font']).metrics('linespace')

    def read_from_file(self, file_path):
        try:
            with open(file_path) as file:
                self.text.delete("1.0", END)
                for line in file:
                    if len(line) > self.max_symbols_per_line:
                        self.max_symbols_per_line = len(line)
                    self.text.insert("end", line.replace('\t', ' ' * const.TAB_SIZE_SYMBOLS))
                self.txt_filter.check_file_ext(file_path)

        except FileNotFoundError:
            self.logger.warning(f"Default file {file_path} not found")


if __name__ == "__main__":
    root = Tk()
    width, height = const.DEFAULT_WINDOW_WIDTH, const.DEFAULT_WINDOW_HEIGHT
    root.geometry(f"{width}x{height}+{int((root.winfo_screenwidth()-width)/2)}+"
                  f"{int((root.winfo_screenheight()-height)/2)}")
    root.minsize(height=height, width=width)
    root.title(const.DEFAULT_WINDOW_TITLE)
    app = App(root)
    root.mainloop()

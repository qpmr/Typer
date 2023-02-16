import sys
import os.path

if sys.version_info < (3, 7, 0):
    raise RuntimeError("Sorry, python 3.7.0 or later is required")

from tkinter import Tk, Text, Label, Scrollbar, Frame, Menu, filedialog, INSERT, ALL, END
import tkinter.font as tkfont

from statistics import Statistics
from state import StateStorage
from processing import TextProcessor
from constants import Constants as const


class App:
    START_POS = "1.0"
    DEFAULT_TEST_PATH = "tests/text.txt"
    _frame_stat_pad = 10
    _text_bottom_symbols_pad = 5

    def __init__(self, root_widget):
        self._restore_pos: bool = False
        self._last_pos: str = self.START_POS

        self.create_menu(root_widget)

        # Setup text widget
        self.text = Text(root_widget, wrap="none")
        self._root = root_widget
        self.text.bind("<KeyPress>", func=self.press_event)
        self.text.bind("<Button-1>", func=self.click)
        try:
            print(os.path.dirname(os.path.realpath(__file__)))
            text = self.read_file(f"{os.path.dirname(os.path.realpath(__file__))}/{self.DEFAULT_TEST_PATH}")
            if text != '':
                self.text.insert("1.0", text)
        except():
            print(f"Default file{os.path.dirname(os.path.realpath(__file__))}/{self.DEFAULT_TEST_PATH} not found")
            pass
        self.text_setup()

        # Setup processing core and state storage
        self.txt_state_storage = StateStorage()
        self.txt_proc = TextProcessor(self.txt_state_storage, self)
        self.txt_stat = Statistics()

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
        self.stat_frame = Frame(root, width=const.STAT_FRAME_WIDTH_SYMBOLS)
        self.stat_frame.grid(row=0, column=2, columnspan=1, sticky="nw", padx=self._frame_stat_pad,
                             pady=self._frame_stat_pad)

        self.label_stat = Label(self.stat_frame, text="Statistics:", width=const.STAT_FRAME_WIDTH_SYMBOLS, anchor="w",
                                font=("TkDefaultFont", 10, "bold"))
        self.label_stat.grid(row=0, column=0, sticky="w")

        self.speed_val_label = Label(self.stat_frame, width=const.STAT_FRAME_WIDTH_SYMBOLS, anchor="w")
        self.speed_val_label.grid(row=1, column=0, sticky="w")

        self.errors_val_label = Label(self.stat_frame, width=const.STAT_FRAME_WIDTH_SYMBOLS, anchor="w")
        self.errors_val_label.grid(row=2, column=0, sticky="w")

        self.upd_stat_gui()

    def upd_stat_gui(self):
        errors, speed = self.txt_stat
        self.speed_val_label.configure(text=f"Speed: %d WPM" % speed)
        self.errors_val_label.configure(text=f"Errors: %d" % errors)

    def text_setup(self):
        self.text.mark_set("current", "1.0")
        self.text.mark_set("insert", "1.0")
        self.text.focus_set()

    def click(self, event):
        if event.num == 1:
            self._restore_pos = True

    def get_line_len(self, line: int):
        return len(self.text.get(f"{line}.0", f"{line}.end"))

    def press_event(self, event):

        if not event.char:
            return

        # Restore cursor position if user clicked in the text
        if self._restore_pos:
            self.text.mark_set("insert", self._last_pos)

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

        if event.keysym == 'space':
            self.txt_stat.one_word_typed()
        if event.keysym == 'Return':
            self.txt_stat.upd_speed()

        self.upd_stat_gui()
        return "break"

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
            text = self.read_file(filename)
            max_symbols_per_line = 0
            for line in text.splitlines():
                if len(line) > max_symbols_per_line:
                    max_symbols_per_line = len(line)

            max_symbols_per_line += 1
            self.txt_state_storage.reset()
            self.text.tag_delete(ALL)
            self.text.delete("1.0", END)
            self.text.insert("1.0", text)
            self.text_setup()
            self.txt_stat.reset()
            self.upd_stat_gui()

            default_font_width = self.get_font_width()

            # If file text doesn't fit to our default window we resize our window
            # but be aware about padding and widgets align
            # TODO screen boundaries
            if default_font_width * max_symbols_per_line > (self._root.winfo_width() - self.stat_frame.winfo_width()):
                new_window_width = default_font_width * max_symbols_per_line + self.stat_frame.winfo_width() + \
                                   self._frame_stat_pad * 2 + self.scroll_y.winfo_width()
                self._root.geometry(f"{new_window_width}x{self._root.winfo_height()}+"
                                    f"{int((root.winfo_screenwidth() - int(new_window_width))/2)}+"
                                    f"{int((root.winfo_screenheight()-int(self._root.winfo_height()))/2)}")
                self.text.config(width=max_symbols_per_line)
                print(self._root.winfo_height(), new_window_width)

    def get_font_width(self):
        if self.text:
            return tkfont.Font(font=self.text['font']).measure('.')
        else:
            return 0

    @staticmethod
    def read_file(filename):
        with open(filename, "r") as file:
            return file.read()


if __name__ == "__main__":
    root = Tk()
    width, height = const.DEFAULT_WINDOW_WIDTH, const.DEFAULT_WINDOW_HEIGHT
    root.geometry(f"{width}x{height}+{int((root.winfo_screenwidth()-int(width))/2)}+"
                  f"{int((root.winfo_screenheight()-int(height))/2)}")
    root.minsize(height=height, width=width)
    root.maxsize(height=root.winfo_screenheight(), width=root.winfo_screenwidth())
    root.title(const.DEFAULT_WINDOW_TITLE)
    app = App(root)
    root.mainloop()

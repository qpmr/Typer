import os.path
import re


class FileFilters:
    C_TYPE = ".c"
    PY_TYPE = ".py"
    FILTER_COMMENTS = "filter_comments"

    def __init__(self, parent):
        self.parent = parent
        self.curr_file_ext = None
        self.file_ext = (self.C_TYPE, self.PY_TYPE)
        self.original_text = ""

    def check_file_ext(self, file_path: str):
        ext = os.path.splitext(file_path)[1]

        if ext in self.file_ext:
            self.curr_file_ext = ext

    def apply_filter(self, filter_type, value):
        if self.curr_file_ext:
            if filter_type == self.FILTER_COMMENTS:
                self.hide_range(value)

    def find_comments(self):
        if self.curr_file_ext == self.C_TYPE:
            text = self.parent.text.get("1.0", "end")

            # The code below was generated by chatGBT
            # Remove multi-line comments
            pattern = re.compile(r'/\*.*?\*/', re.DOTALL)
            text = pattern.sub('', text)

            # Remove single-line comments
            pattern = re.compile(r'^\s*//.*$', re.MULTILINE)
            text = pattern.sub('', text)

            # Remove empty lines
            pattern = re.compile(r'^\s*\n', re.MULTILINE)
            text = pattern.sub('', text)

            self.parent.text.delete("1.0", "end")
            self.parent.text.insert("1.0", text)

        elif self.curr_file_ext == self.PY_TYPE:
            pattern = re.compile(r'#[^\'"]*$|""".*?"""|\'\'\'.*?\'\'\'|#[^\'"]*$', re.MULTILINE | re.DOTALL)

            # Get the text from the Text widget
            text = self.parent.text.get("1.0", "end")

            # Remove all the matches from the text
            new_text = pattern.sub("", text)

            # Set the updated text to the Text widget
            self.parent.text.delete("1.0", "end")
            self.parent.text.insert("1.0", new_text)

    def hide_range(self, cmd):
        if cmd:
            self.original_text = self.parent.text.get("1.0", "end")
            self.find_comments()
        else:
            self.parent.text.delete("1.0", "end")
            self.parent.text.insert("1.0", self.original_text)

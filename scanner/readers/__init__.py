"""Reader registry. Textual always. Language readers are optional attachments."""

from scanner.readers.python_ast import read_python
from scanner.readers.textual import read_textual

LANG_READERS = {
    "python": read_python,
}

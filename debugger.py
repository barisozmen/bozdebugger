import os
import sys
import linecache

from collections import namedtuple, defaultdict
from contextlib import ContextDecorator, nullcontext
from dataclasses import dataclass

from typing import ClassVar, Dict

import functools



@functools.lru_cache(maxsize=None)
def getenv(key:str, default=0): return type(default)(os.getenv(key, default))

class ContextVar:
  _cache: ClassVar[Dict[str, 'ContextVar']] = {}
  value: int
  def __new__(cls, key, default_value):
    if key in ContextVar._cache: return ContextVar._cache[key]
    instance = ContextVar._cache[key] = super().__new__(cls)
    instance.value = getenv(key, default_value)
    return instance
  def __bool__(self): return bool(self.value)
  def __ge__(self, x): return self.value >= x
  def __gt__(self, x): return self.value > x
  def __lt__(self, x): return self.value < x


LINEPRINTING = ContextVar('LINEPRINTING', 0)




Color = namedtuple('Color', ['name', 'code'])

basic_color_list = [
    # 'black': '\033[30m',
    # 'white': '\033[37m',
    Color('red', '\033[31m'),
    Color('green', '\033[32m'),
    Color('yellow', '\033[33m'),
    Color('blue', '\033[34m'),
    Color('magenta', '\033[35m'),
    Color('cyan', '\033[36m'),
    Color('reset', '\033[0m'),
    Color('background_black', '\033[40m'),
    Color('background_red', '\033[41m'),
    Color('background_blue', '\033[44m'),
    Color('background_magenta', '\033[45m'),
    Color('background_cyan', '\033[46m'),
    Color('background_white', '\033[47m'),
    Color('background_bright_black', '\033[100m'),
    Color('background_bright_red', '\033[101m'),
    Color('background_bright_green', '\033[102m'),
    Color('background_bright_yellow', '\033[103m'),
    Color('background_bright_blue', '\033[104m'),
    Color('background_bright_magenta', '\033[105m'),
    Color('background_bright_cyan', '\033[106m'),
    Color('background_bright_white', '\033[107m'),
    Color('bright_red', '\033[91m'),
    Color('bright_green', '\033[92m'),
    Color('bright_yellow', '\033[93m'),
    Color('bright_blue', '\033[94m'),
    Color('bright_magenta', '\033[95m'),
    Color('bright_cyan', '\033[96m'),
    Color('bright_white', '\033[97m'),
]

def make_color_list_for_code_stack():
    color_list = []
    for bg_color in range(41, 48):
        # for fg_color in range(30, 38):
            bg_color_code = f'\033[{bg_color}m'
            fg_color_code = f'\033[{30}m'
            color_list.append(Color(f'bg{bg_color}_fg{30}', bg_color_code + fg_color_code))
    return color_list

code_stack_color_list = make_color_list_for_code_stack()
color_dict = {color.name: color.code for color in basic_color_list + code_stack_color_list}


def singleton_factory(cls):
    instances = {}
    def get_the_instance(*args, **kwargs):
        if cls not in instances:
            instances[cls] = cls(*args, **kwargs)
        return instances[cls]
    return get_the_instance


FILE_NAME = 'line_history.txt'
class FileManager:
    def __init__(self, file_name=FILE_NAME):
        self.file_name = file_name
        self.has_written_any = False

    def write(self, text):
        if not self.has_written_any:
            self._remove_file()
            self.has_written_any = True
        with open(self.file_name, 'a') as f:
            f.write(text + '\n')

    def _remove_file(self):
        try:
            os.remove(self.file_name)
        except FileNotFoundError:
            pass

file_manager = singleton_factory(FileManager)(FILE_NAME)

class ColorAssigner:
    def __init__(self):
        self.assigned_colors = {}
        self.color_index = 0

    def __call__(self, name):
        if name in self.assigned_colors:
            return self.assigned_colors[name]
        color = code_stack_color_list[self.color_index]
        self.color_index = (self.color_index + 1) % len(code_stack_color_list)
        self.assigned_colors[name] = color
        return color


color_assigner = singleton_factory(ColorAssigner)()



class Coloring(ContextDecorator):
    def __init__(self, *args, color=None, by=None):
        assert (color is not None or len(args)==1) or by is not None
        if by is not None:
            self.color_code = color_assigner(by).code
        else:
            color_name = color if color else args[0]
            if color_name not in color_dict: 
                print(f'{color_name} is not allowed')
                raise ValueError(f"Color {color_name} not found.")
            self.color_code = color_dict[color_name]

    def __call__(self, *args, **kwargs):
        return self.__str__(*args, **kwargs)

    def __str__(self, *args):
        return ' '.join([self.color_code + str(arg) + color_dict['reset'] for arg in args])
    
    def __enter__(self):
        print(self.color_code, end='')
    
    def __exit__(self, *exc):
        print(color_dict['reset'], end='')


flag_prev_print_vars = {}



@dataclass
class Line:
    filename: str
    funcname: str
    lineno: int
    execution_count: int=0
    total_time_spent: float=0
    
    def __post_init__(self):
        self.resolve_line_str()

    def resolve_line_str(self):
        self.line = linecache.getline(self.filename, self.lineno).rstrip()

    def __str__(self): return f"{self.filename} {self.lineno}: {self.line} ({self.count})"
    def __repr__(self): return f"Line({self.filename}, {self.lineno}, {self.line})"



FILE_NAME = 'line_history.txt'
class FileManager:
    def __init__(self, file_name=FILE_NAME):
        self.file_name = file_name
        self.has_written_any = False

    def write(self, text):
        if not self.has_written_any:
            self._remove_file()
            self.has_written_any = True
        with open(self.file_name, 'a') as f:
            f.write(text + '\n')

    def _remove_file(self):
        try:
            os.remove(self.file_name)
        except FileNotFoundError:
            pass

_the_file_manager = None

def the_file_manager(file_name=FILE_NAME):
    global _the_file_manager
    if _the_file_manager is None:
        _the_file_manager = FileManager(file_name)
    return _the_file_manager


file_manager = the_file_manager()



line_history = []

line_execution_counts = defaultdict(int)


@dataclass
class LineExecution:
    filename: str
    funcname: str
    lineno: int
    stack_level: int
    line_str: str = None
        
    def __post_init__(self):
        self.resolve_line_str()
        self.resolve_line_execution_count()
        line_history.append(self)
        return self

    def resolve_stack_level(self, frame):
        self.stack_level = 0
        while frame:
            self.stack_level += 1
            frame = frame.f_back

    def resolve_line_str(self):
        global line_history
        self.line_str = linecache.getline(self.filename, self.lineno).rstrip()

        most_recent_line_execution_from_above_function = next((line for line in reversed(line_history) if line.funcname != self.funcname and line.stack_level < self.stack_level), None)
        
        if most_recent_line_execution_from_above_function is None:
            return

        prev_line_leading_ws = self._count_leading_whitespaces(most_recent_line_execution_from_above_function.line_str)
        self_line_leading_ws = self._count_leading_whitespaces(self.line_str)
        
        if ((extra_ws:=(prev_line_leading_ws - self_line_leading_ws)) >= 0):
            self.line_str = ' '*(4+extra_ws) + self.line_str

    def resolve_line_execution_count(self):
        line_execution_counts[(self.filename, self.lineno)]+=1
        self.line_execution_count = line_execution_counts[(self.filename, self.lineno)]

    def __str__(self): 
        MAX_LEN = 90
        address_equal_length = (address:=f'{self.filename} ___{self.funcname}()')[-MAX_LEN:]  + '_' * (max(0, MAX_LEN-len(address)))
        main_part = f"stack_level=[{self.stack_level}]__ {address_equal_length}{self.lineno}:{self.line_str}"
        return main_part + " "*(MAX_LEN+80-len(main_part)) + f"  __x{self.line_execution_count}"

    def print(self):
        with Coloring(by=self.filename):
            print(str(self))
            file_manager.write(Coloring(by=self.filename)(str(self)))

    def _count_leading_whitespaces(self, line): return len(line) - len(line.lstrip())


def trace_lines(frame, event, arg):
    global flag_prev_funcname

    if event != 'line':
        return trace_lines
    
    filename = frame.f_globals["__file__"]
    funcname = frame.f_code.co_name
    lineno = frame.f_lineno
    stack_level = 0
    f=frame
    while f:
        stack_level += 1
        f = f.f_back
    line_execution = LineExecution(
        filename=filename,
        funcname=funcname,
        lineno=lineno,
        stack_level=stack_level
    )
    line_execution.print()

    return trace_lines

def trace_calls(frame, event, arg):
    if event != 'call':
        return
    # Filter out calls not belonging to the script itself.
    if frame.f_code.co_filename.startswith('<') and frame.f_code.co_filename.endswith('>'):
        return
    return trace_lines


class LinePrinting(ContextDecorator):
    def __enter__(self):
        sys.settrace(trace_calls)
        return self

    def __exit__(self, *exc):
        sys.settrace(None)
        return False



def another_function(x):
    x=3
    return x**2


def main():
    # Example function to demonstrate tracing.
    def test_function():
        for i in range(3):
            print(i)
            another_function(x=4)

    test_function()

if __name__ == "__main__":
    LINEPRINTING=1
    with LinePrinting() if LINEPRINTING>0 else nullcontext():
        main()


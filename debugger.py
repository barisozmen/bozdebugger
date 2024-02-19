import os
import sys
import linecache

from collections import namedtuple
from contextlib import ContextDecorator, nullcontext




def getenv(key:str, default=0): return type(default)(os.getenv(key, default))

LINEPRINTING = getenv('LINEPRINTING')




Color = namedtuple('Color', ['name', 'code'])

color_list = [
    # 'black': '\033[30m',
    # 'white': '\033[37m',
    Color('red', '\033[31m'),
    Color('green', '\033[32m'),
    Color('yellow', '\033[33m'),
    Color('blue', '\033[34m'),
    Color('magenta', '\033[35m'),
    Color('cyan', '\033[36m'),
    Color('reset', '\033[0m'),
    Color('bright_black', '\033[90m'),
    Color('bright_red', '\033[91m'),
    Color('bright_green', '\033[92m'),
    Color('bright_yellow', '\033[93m'),
    Color('bright_blue', '\033[94m'),
    Color('bright_magenta', '\033[95m'),
    Color('bright_cyan', '\033[96m'),
    Color('bright_white', '\033[97m'),
    Color('background_black', '\033[40m'),
    Color('background_red', '\033[41m'),
    Color('background_green', '\033[42m'),
    Color('background_yellow', '\033[43m'),
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
    Color('background_bright_white', '\033[107m')
]

color_dict = {color.name: color.code for color in color_list}



class ColorAssigner:
    def __init__(self):
        self.assigned_colors = {}
        self.color_index = 0

    def __call__(self, name):
        if name in self.assigned_colors:
            return self.assigned_colors[name]
        color = color_list[self.color_index]
        self.color_index = (self.color_index + 1) % len(color_list)
        self.assigned_colors[name] = color
        return color

_the_color_assigner = None

def the_color_assigner():
    global _the_color_assigner
    if _the_color_assigner is None:
        _the_color_assigner = ColorAssigner()
    return _the_color_assigner


color_assigner = the_color_assigner()


class Colored:
    def __init__(self, *args, color=None, _for=None):
        assert (color is not None or len(args)==1) or _for is not None
        if _for is not None:
            self.color_code = color_assigner(_for).code
        else:
            color_name = color if color else args[0]
            if color_name not in color_dict: 
                print(f'{color_name} is not allowed')
                raise ValueError(f"Color {color_name} not found.")
            self.color_code = color_dict[color_name].code

    def __call__(self, *args, **kwargs):
        return self.__str__(*args, **kwargs)

    def __str__(self, *args):
        return ' '.join([self.color_code + str(arg) + self.color_code for arg in args])
    
    def __repr__(self):
        return self.__str__()

def trace_lines(frame, event, arg):
    if event != 'line':
        return trace_lines
    # Retrieve the current file name and line number.
    filename = frame.f_globals["__file__"]
    lineno = frame.f_lineno
    line = linecache.getline(filename, lineno).rstrip()

    # Determine the function name
    funcname = frame.f_code.co_name

    # Print the filename, line number, and code; with color. 
    print(Colored(_for=funcname)(f"{filename}:{lineno}: {line}"))

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

def another_function():
    x=3
    return x**2


def main():
    # Example function to demonstrate tracing.
    def test_function():
        for i in range(3):
            print(i)
            another_function()

    test_function()

if __name__ == "__main__":
    with LinePrinting() if LINEPRINTING>0 else nullcontext():
        main()


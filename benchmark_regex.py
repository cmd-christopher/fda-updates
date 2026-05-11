import time
import re

text = "1.1 Heading 1\nSome text\n2.1 Heading 2\nMore text\n" * 1000

# Original code
def original():
    sections = []
    last_end = 0
    for m in re.finditer(r"(?:^|[\s\)])(\d+(?:\.\d+)+)\s+([A-Z])", text):
        num = m.group(1)
        num_start = m.start() + m.group(0).find(num)
        title_start = m.end() - len(m.group(2))

# Optimized code
HEADING_REGEX = re.compile(r"(?:^|[\s\)])(\d+(?:\.\d+)+)\s+([A-Z])")

def optimized():
    sections = []
    last_end = 0
    for m in HEADING_REGEX.finditer(text):
        num = m.group(1)
        num_start = m.start() + m.group(0).find(num)
        title_start = m.end() - len(m.group(2))

# Benchmark
import timeit

print("Original:", timeit.timeit(original, number=1000))
print("Optimized:", timeit.timeit(optimized, number=1000))

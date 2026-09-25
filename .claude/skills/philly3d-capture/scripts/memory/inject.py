#!/usr/bin/env python3
"""Stage a build with the WebGL memory hook injected at the top of <head> (before three.js and the page run).
usage: python3 inject.py <in.html> <out.html>   (both usually in the scratchpad's serve/ directory)"""
import sys
from pathlib import Path
hook = (Path(__file__).parent / 'gpuhook.js').read_text()
s = Path(sys.argv[1]).read_text(encoding='utf-8')
i = s.index('<head>') + len('<head>')
Path(sys.argv[2]).write_text(s[:i] + '<script>' + hook + '</script>' + s[i:], encoding='utf-8')
print('wrote', sys.argv[2])

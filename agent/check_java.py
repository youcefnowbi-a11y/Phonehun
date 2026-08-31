import re, glob, os
bad = False
total = 0
for f in sorted(glob.glob('agent/src/com/lo/syskit/*.java')):
    src = open(f, encoding='utf-8').read()
    total += len(src)
    s = re.sub(r'"(\\.|[^"\\])*"', '""', src)   # blank strings
    s = re.sub(r'//.*', '', s)                   # line comments
    s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)  # block comments
    ob, cb, po, pc = s.count('{'), s.count('}'), s.count('('), s.count(')')
    ok = ob == cb and po == pc
    if not ok:
        bad = True
    name = os.path.basename(f)
    print(('OK  ' if ok else 'BAD ') + f'{name:20} braces {ob}/{cb}  parens {po}/{pc}')
print('JAVA BALANCE:', 'FAIL' if bad else 'ALL OK')
print(f'source total: {total/1024:.1f} KB of Java')

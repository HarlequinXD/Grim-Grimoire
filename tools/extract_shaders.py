"""Extract the GLSL constants from Shaders.java so CI can validate them with glslangValidator."""
import os, re, sys
src, out = sys.argv[1], sys.argv[2]
os.makedirs(out, exist_ok=True)
text = open(src).read()
for name, body in re.findall(r'public static final String (\w+) =\s*((?:\s*"(?:[^"\\]|\\.)*"\s*\+?)+);', text):
    glsl = ''.join(bytes(s, 'utf-8').decode('unicode_escape') for s in re.findall(r'"((?:[^"\\]|\\.)*)"', body))
    ext = '.vert' if name.endswith('_VS') else '.frag'
    open(os.path.join(out, name + ext), 'w').write('#version 100\n' + glsl)
    print('extracted', name + ext)

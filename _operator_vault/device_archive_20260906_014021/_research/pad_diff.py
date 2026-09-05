from PIL import Image, ImageChops
import numpy as np, sys
a = Image.open(sys.argv[1]).convert('RGB'); b = Image.open(sys.argv[2]).convert('RGB')
arr = np.array(ImageChops.difference(a,b)).sum(axis=2)
changed = arr > 30
print('TOTAL:', int(changed.sum()))
print('PAD:', int(changed[937:1383, 137:583].sum()), '| CLOCK:', int(changed[150:260, 100:620].sum()), '| STATUSBAR:', int(changed[0:60, 0:720].sum()))
print('BBOX:', ImageChops.difference(a,b).getbbox())
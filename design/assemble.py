import re
tpl=open('comparison.template.html',encoding='utf-8').read()
parts=open('_merged-parts.html',encoding='utf-8').read()
blocks=dict(re.findall(r'<section class="variant v(\w)"[^>]*>(.*?)</section>',parts,re.S))
for k,v in blocks.items():
    tpl=tpl.replace(f'<!--MOCKUP_{k.upper()}-->',v)
allcss=re.findall(r'<style>\n(.*?)\n</style>',parts,re.S)
tpl=tpl.replace('</head>', '\n'.join(f'<style>\n{c}\n</style>' for c in allcss)+'\n</head>')
assert '<!--MOCKUP' not in tpl
open('comparison.html','w',encoding='utf-8').write(tpl)
print("bytes:",len(tpl),"| shots:",tpl.count('class="shot"'))

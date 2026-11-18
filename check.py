#!/usr/bin/env python3
"""Run before publishing: python3 check.py. Original source IDs must remain stable."""
import json,re,html,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
lib=json.loads((ROOT/'data/library.json').read_text());releases=json.loads((ROOT/'data/releases.json').read_text())
problems=[]
def check(condition,message):
 if not condition:problems.append(message)
raw=(ROOT/'source/original-upload.html').read_text()
def plain(s):return html.unescape(re.sub('<[^>]+>','',s)).strip()
def part(id):return re.search(r'<section[^>]+id="'+id+r'"[^>]*>(.*?)</section>',raw,re.S).group(1)
original_p2=[plain(re.search(r'<div class="answer">(.*?)</div>',a,re.S).group(1)) for a in re.findall(r'<article\b.*?</article>',part('p2'),re.S)]
check(len(lib['part1'])==18,'Part 1 source topics changed')
check(sum(len(x['questions']) for x in lib['part1'])==23,'Part 1 unique answer count changed')
check(len(lib['part3'])==10 and sum(len(x['questions']) for x in lib['part3'])==37,'Part 3 source count changed')
for i,answer in enumerate(original_p2,1):
 q=next((q for q in lib['part2'] if q['id']==f'p2-{i:02}'),None)
 check(q is not None and q['answer']==answer,f'Original P2-{i:02} answer was lost or altered')
source_p3=[plain(a) for a in re.findall(r'<div class="answer"[^>]*>(.*?)</div>',part('p3'),re.S)]
check(source_p3==[q['answer'] for t in lib['part3'] for q in t['questions']],'Part 3 source answers changed')
source_p1=[[plain(a) for a in re.findall(r'<p>(.*?)</p>',topic,re.S)] for topic in re.findall(r'<article\b.*?</article>',part('p1'),re.S)]
check([list(dict.fromkeys(a)) for a in source_p1]==[[q['answer'] for q in t['questions']] for t in lib['part1']],'Unique Part 1 source answers changed')
ids=[q['id'] for q in lib['part2']]+[q['id'] for t in lib['part1']+lib['part3'] for q in t['questions']]
check(len(ids)==len(set(ids)),'Question IDs are not unique')
check(len(lib['groups'])==13,'Expected 13 mother-story groups')
check(len(lib['part2'])==37,'Expected 29 source and 8 generated transfer questions')
for g in lib['groups']:
 cards=[q for q in lib['part2'] if q['group_id']==g['id']]
 check(len(cards)>=2,f'{g["id"]} has no transfer practice')
 corpus=' '.join(q['answer'] for q in cards if q['source_type']=='uploaded')
 for p in g['phrases']:
  check(p['en'].lower() in p['source'].lower() and p['source'] in corpus,f'{g["id"]}: phrase source mismatch')
for q in lib['part2']:
 check(len(q['cue_points'])==4 and all(q['cue_points']),q['id']+': incomplete cue card')
 check(all(q.get(k) for k in ['reference','focus','reuse','adaptation','cue_source']),q['id']+': incomplete transfer information')
 check(any(g['id']==q['group_id'] for g in lib['groups']),q['id']+': invalid group')
check(len(lib['expression_groups'])==6,'Original common-expression groups missing')
check(lib['meta']['version']==releases[-1]['version'],'Version metadata differs')
check('v'+lib['meta']['version'] in (ROOT/'index.html').read_text(),'HTML version differs')
check('## '+lib['meta']['version'] in (ROOT/'CHANGELOG.md').read_text(),'Missing changelog')
if problems:
 print('\n'.join('ERROR: '+p for p in problems));sys.exit(1)
print(f"PASS v{lib['meta']['version']}: 18 Part 1 topics / 23 unique answers; 13 stories / 29 original + 8 added Part 2; 37 preserved Part 3 answers.")

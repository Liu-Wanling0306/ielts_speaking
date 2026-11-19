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
check(sum(len(x['questions']) for x in lib['part1'])==119,'Part 1 question count differs')

check(sum(len(x['questions']) for x in lib['part3'])==162,'Part 3 question count differs')
for i,answer in enumerate(original_p2,1):
 q=next((q for q in lib['part2'] if q['id']==f'p2-{i:02}'),None)
 check(q is not None and q['answer']==answer,f'Original P2-{i:02} answer was lost or altered')
source_p3=[plain(a) for a in re.findall(r'<div class="answer"[^>]*>(.*?)</div>',part('p3'),re.S)]
p3original=sorted([q for t in lib['part3'] for q in t['questions'] if re.fullmatch(r'p3-\d+-\d+',q['id'])],key=lambda q:tuple(map(int,q['id'].split('-')[1:])))
check(source_p3==[q['answer'] for q in p3original],'Part 3 source answers changed')
source_p1=[[plain(a) for a in re.findall(r'<p>(.*?)</p>',topic,re.S)] for topic in re.findall(r'<article\b.*?</article>',part('p1'),re.S)]
p1lookup={q['id']:q for t in lib['part1'] for q in t['questions']}
for i,answers in enumerate(source_p1,1):
 for j,a in enumerate(dict.fromkeys(answers),1):
  q=p1lookup.get(f'p1-{i:02}-{j}')
  check(q is not None and q['answer']==a,f'Original P1-{i}-{j} changed')
ids=[q['id'] for q in lib['part2']]+[q['id'] for t in lib['part1']+lib['part3'] for q in t['questions']]
check(len(ids)==len(set(ids)),'Question IDs are not unique')
check(len(lib['groups'])==13,'Expected 13 mother-story groups')
check(len(lib['part2'])==39,'Expected 29 source + 8 transfers + 2 PDF missing cards')
for g in lib['groups']:
 cards=[q for q in lib['part2'] if q['group_id']==g['id']]
 check(len(cards)>=2,f'{g["id"]} has no transfer practice')
 corpus=' '.join(q['answer'] for q in cards if q['source_type']=='uploaded')
 for p in g['phrases']:
  check(p['en'].lower() in p['source'].lower() and p['source'] in corpus,f'{g["id"]}: phrase source mismatch')
for q in lib['part2']:
 check(len(q['cue_points']) in [4,5] and all(q['cue_points']),q['id']+': incomplete cue card')
 check(all(q.get(k) for k in ['reference','focus','reuse','adaptation','cue_source']),q['id']+': incomplete transfer information')
 check(any(g['id']==q['group_id'] for g in lib['groups']),q['id']+': invalid group')
check(len(lib['expression_groups'])==6,'Original common-expression groups missing')
check(lib['meta']['version']==releases[-1]['version'],'Version metadata differs')
check('v'+lib['meta']['version'] in (ROOT/'index.html').read_text(),'HTML version differs')
check('## '+lib['meta']['version'] in (ROOT/'CHANGELOG.md').read_text(),'Missing changelog')
audit=json.loads((ROOT/'data/forecast-audit.json').read_text())
check(audit==lib['meta']['forecast_audit'],'Audit payload differs')
allq={q['id']:q for t in lib['part1']+lib['part3'] for q in t['questions']};allq.update({q['id']:q for q in lib['part2']})
for part,count in [('part1',105),('part2',29),('part3',129)]:
 rows=[x for x in audit['mapping'] if x['part']==part]
 check(len(rows)==count and len({x['forecast_id'] for x in rows})==count,part+' forecast inventory incomplete')
 for row in rows:
  q=allq.get(row['site_id'])
  check(q is not None and q.get('forecast_id')==row['forecast_id'],row['forecast_id']+' broken mapping')
  check(all(1<=p<=73 for p in row['pages']),row['forecast_id']+' invalid source pages')
  if part=='part2':check(q['cue_points']==row['cue_points'],row['forecast_id']+' cue card differs')
for part in ['part1','part2','part3']:
 qs=lib[part] if part=='part2' else [q for t in lib[part] for q in t['questions']]
 for q in qs:
  wc=len(re.findall(r"[A-Za-z]+(?:['’-][A-Za-z]+)*",q['reference']))
  check(wc==q['reference_words'],q['id']+' wrong word count')
  if not q.get('length_exception'):
   lo,hi={'part1':(40,60),'part2':(215,265),'part3':(90,120)}[part]
   check(lo<=wc<=hi,q['id']+f' length outside target: {wc}')
  if part=='part1' and not q.get('length_exception'):
   check(len(re.split(r'(?<=[.!?])\s+',q['reference']))==4,q['id']+' Part 1 reference is not four sentences')
  check(q['personalization_needed']==bool(re.search(r'\[[^]]+\]',q['reference'])),q['id']+' template status missing')
  sentences=re.split(r'(?<=[.!?])\s+',q['reference'])
  check(len(sentences)==len(set(sentences)),q['id']+' repeated sentence in expanded reference')
hometown=next(q for q in allq.values() if q.get('forecast_id')=='pdf-p1-03-01')
check(not re.search(r"\b(?:like|love|enjoy|favourite|miss)\b",hometown['reference'],re.I),'Factual hometown question contains unrequested preference')
check(lib['meta']['storage_key']=='ieltsSpeaking:user:v1','Storage compatibility changed')
# These checks protect confirmed biography/preferences that were wrong in the earlier generic models.
forecast1={q.get('forecast_id'):q for t in lib['part1'] for q in t['questions'] if q.get('forecast_id')}
check('Vannie' in forecast1['pdf-p1-01-01']['reference'],'Preferred name not updated')
check('Kunming' in forecast1['pdf-p1-04-01']['reference'] and 'sister' in forecast1['pdf-p1-04-01']['reference'],'Current home incorrect')
check(forecast1['pdf-p1-08-01']['reference'].startswith('Not usually'),'Shopping-list preference incorrect')
check('tablet' in forecast1['pdf-p1-11-05']['reference'] and 'choose a computer' not in forecast1['pdf-p1-11-05']['reference'],'Tablet preference incorrect')
check(forecast1['pdf-p1-16-02']['reference'].startswith('Yes'),'Selfie preference incorrect')
check('washing machine' in forecast1['pdf-p1-18-01']['reference'].lower(),'Main household machine incorrect')
check(forecast1['pdf-p1-02-02'].get('not_applicable') is True,'Work branch not labelled')
check(sum(q['personalization_needed'] for q in forecast1.values())==6,'Remaining personal fact status differs')
check(lib['meta']['part1_target_seconds']==[20,30],'Part 1 timing metadata incorrect')
for row in audit['mapping']:
 q=allq[row['site_id']]
 check(row['reference_words']==q['reference_words'] and row['personalization_needed']==q['personalization_needed'],row['forecast_id']+' audit status stale')
for part,expected in [('part1',8),('part3',9)]:
 categories=lib['topic_categories'][part];keys={c['id'] for c in categories}
 check(len(keys)==len(categories)==expected,part+' invalid category catalog')
 qs=[q for t in lib[part] for q in t['questions']]
 for t in lib[part]:
  check(bool(t.get('display_title')),t['id']+' missing human-readable topic')
  for q in t['questions']:check(q.get('category_id') in keys,q['id']+' missing/invalid classification')
 for key in keys:check(any(q.get('category_id')==key for q in qs),part+' empty category '+key)
 for row in audit['mapping']:
  if row['part']==part:check(row.get('category_id')==allq[row['site_id']]['category_id'],row['forecast_id']+' stale category in audit')
check(allq['pdf-p3-11-04']['category_id']=='education','School popularity classified under workplace')
check(allq['pdf-p3-05-06']['category_id']=='work','Business humour classified only under comedy')
check(allq['pdf-p3-25-03']['category_id']=='education','Instrument learning classified only under music')
mock=lib.get('mock_exam',{})
check(mock.get('part1_seconds')==270 and mock.get('part3_seconds')==270,'Mock section timing differs')
check(mock.get('preparation_seconds')==60 and mock.get('long_turn_seconds')==120,'Mock long-turn timing differs')
all_topics={t['id'] for t in lib['part3']}
for q in lib['part2']:
 link=mock.get('links',{}).get(q['id'],{})
 check(len(link.get('wrap_up',[]))==2 and all(link.get('wrap_up',[])),q['id']+' missing mock wrap-up')
 check(bool(link.get('part3_topic_ids')) and all(t in all_topics for t in link.get('part3_topic_ids',[])),q['id']+' invalid linked discussion topics')
 check(all(id in allq for id in link.get('part3_question_ids',[])),q['id']+' invalid linked discussion question')
for file in ['mock-core.js','mock-exam.js','tests/verify_mock_core.js','tests/verify_mock_ui.py']:
 check((ROOT/file).exists(),'Missing mock module/check '+file)
if problems:
 print('\n'.join('ERROR: '+p for p in problems));sys.exit(1)
print(f"PASS v{lib['meta']['version']}: all original answers/IDs preserved; PDF coverage 105/105 + 29/29 + 129/129; reference lengths, cue cards and template status checked.")

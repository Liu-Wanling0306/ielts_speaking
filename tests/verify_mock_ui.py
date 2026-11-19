"""Whole-Part mock flow: manual progression, question speech before timing, persistence and backups."""
import asyncio,json,os,shutil,tempfile
from pathlib import Path
from playwright.async_api import async_playwright
SPEECH_STUB='''(() => {
 class Utterance {constructor(text){this.text=text}}
 const synth={getVoices:()=>[{lang:'en-GB',name:'Test English'}],speak(u){window.__utterances.push(u);window.__pending=u;window.__lastUtterance=u;if(window.__voiceMode==='error'){u.onerror?.({error:'voice-unavailable'});return}u.onstart?.()},cancel(){window.__cancelled++;window.__pending=null}};
 Object.defineProperty(window,'SpeechSynthesisUtterance',{value:Utterance,configurable:true});Object.defineProperty(window,'speechSynthesis',{value:synth,configurable:true});
 window.__utterances=[];window.__pending=null;window.__cancelled=0;window.__voiceMode='manual';window.__endSpeech=()=>{const u=window.__pending;window.__pending=null;u?.onend?.()};window.__testSynth=synth;
})()'''
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None)
  page=await browser.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=True);await page.add_init_script(SPEECH_STUB);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(os.environ.get('SPEAKING_TEST_URL','http://127.0.0.1:8001'));await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=mock]').click()
  await page.locator('[data-mock-action=begin]').click();session=await page.evaluate('USER.mock.active.id');await page.locator('[data-mock-action=resume]').click()
  counts=await page.evaluate("Object.fromEntries(['p1','p2','p3','wrap'].map(k=>[k,USER.mock.active.steps.filter(s=>s.kind===k).length]))")
  assert await page.locator('[data-mock-part=p1]').count()==1 and await page.locator('.mock-exam-row').count()==counts['p1']
  assert not await page.evaluate('USER.mock.active.running')
  first=await page.evaluate('USER.mock.active.steps[USER.mock.active.index].qid');initial=await page.locator('#mockCountdown').inner_text()
  await page.locator('[data-mock-action=resume]').click()
  assert await page.evaluate('__utterances.length')==1
  assert await page.evaluate('__utterances[0].text')==await page.evaluate('(id)=>MOCK_EXAM.bank.all.get(id).question',first)
  assert await page.evaluate('__utterances[0].lang')=='en-GB'
  await page.wait_for_timeout(300);assert initial==await page.locator('#mockCountdown').inner_text();assert not await page.evaluate('USER.mock.active.running')
  assert await page.locator('[data-mock-action=next]').is_disabled()
  await page.evaluate('__endSpeech()');await page.wait_for_function('USER.mock.active.running')
  await page.locator('[data-mock-action=pause]').click();paused=await page.locator('#mockCountdown').inner_text();await page.wait_for_timeout(250);assert paused==await page.locator('#mockCountdown').inner_text()
  voice_count=await page.evaluate('__utterances.length');await page.locator('[data-mock-action=resume]').click();assert await page.evaluate('__utterances.length')==voice_count
  await page.locator('[data-mock-action=listen]').click();assert not await page.evaluate('USER.mock.active.running');await page.evaluate('__endSpeech()')
  async def expire():
   index=await page.evaluate('USER.mock.active.index')
   await page.evaluate('USER.mock.active.remainingMs=10;USER.mock.active.tickAt=Date.now()-30')
   await page.wait_for_function('USER.mock.active.remainingMs===0&&!USER.mock.active.running')
   await page.wait_for_timeout(300)
   assert await page.evaluate('USER.mock.active.index')==index
   assert await page.evaluate('USER.mock.active.status')=='exam'
   assert '不会自动换题' in await page.locator('#mockTimerStatus').inner_text()
  await expire();assert await page.evaluate('(id)=>!USER.mock.ratings[id]',first)
  await page.locator('[data-mock-action=next]').click();assert await page.evaluate('(id)=>USER.mock.ratings[id].level',first)=='unrated'
  assert await page.locator('.mock-exam-row').count()==counts['p1'] and not await page.evaluate('USER.mock.active.running')
  second=await page.evaluate('USER.mock.active.steps[USER.mock.active.index].qid')
  await page.locator('[data-mock-action=skip]').click();assert await page.evaluate('(id)=>!USER.mock.ratings[id]',second)
  # A delayed speech callback may not start a timer after leaving the mock page.
  await page.locator('[data-mock-action=resume]').click();await page.evaluate('window.__staleSpeech=window.__pending')
  index=await page.evaluate('USER.mock.active.index');await page.locator('.nav [data-page=p1]').click();await page.evaluate('__staleSpeech.onend()');assert not await page.evaluate('USER.mock.active.running')
  await page.locator('.nav [data-page=mock]').click();assert await page.evaluate('USER.mock.active.index')==index
  await page.locator('[data-mock-action=resume]').click();await page.evaluate('__endSpeech()');await page.locator('[data-mock-action=pause]').click()
  remaining=await page.evaluate('USER.mock.active.remainingMs');await page.reload();await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=mock]').click()
  assert await page.evaluate('USER.mock.active.id')==session and await page.evaluate('USER.mock.active.index')==index
  assert abs(await page.evaluate('USER.mock.active.remainingMs')-remaining)<100 and not await page.evaluate('USER.mock.active.running')
  async def complete_current():
   if not await page.evaluate('USER.mock.active.stepStarted'):
    await page.locator('[data-mock-action=resume]').click();await page.evaluate('__endSpeech()')
   await page.locator('[data-mock-action=next]').click()
  while not await page.evaluate('USER.mock.active.partComplete'):await complete_current()
  assert await page.locator('[data-mock-part=p1]').count()==1 and await page.locator('.mock-exam-row').count()==counts['p1']
  await page.wait_for_timeout(300);assert await page.locator('[data-mock-part=p2]').count()==0
  await page.reload();await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=mock]').click()
  assert await page.evaluate('USER.mock.active.partComplete') and await page.locator('[data-mock-part=p1]').count()==1
  assert await page.locator('[data-mock-action=next-part]').is_enabled() and await page.evaluate('__utterances.length')==0
  await page.locator('[data-mock-action=next-part]').click()
  assert await page.locator('[data-mock-part=p2]').count()==1 and await page.locator('.mock-exam-row').count()==4
  assert await page.locator('[data-step-kind=wrap]').count()==2 and await page.locator('[data-step-kind=wrap]').first.is_visible()
  assert await page.locator('.reference').count()==0
  p2id=await page.evaluate('USER.mock.active.part2Id');await page.locator('#mockNotes').fill('setting / change / reflection')
  await page.locator('[data-mock-action=resume]').click();spoken=await page.evaluate('__utterances.at(-1).text');assert 'You should say:' in spoken
  await page.evaluate('__endSpeech()');assert await page.locator('#mockCountdown').inner_text()=='01:00';await page.locator('#mockNotes').focus();await expire();assert await page.evaluate('document.activeElement.id')=='mockNotes'
  assert await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='prep' and await page.evaluate('(id)=>!USER.mock.ratings[id]',p2id)
  await page.locator('[data-mock-action=next]').click();assert await page.locator('.mock-exam-row').count()==4
  assert await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='p2'
  await page.locator('[data-mock-action=resume]').click();assert 'one to two minutes' in await page.evaluate('__utterances.at(-1).text');await page.evaluate('__endSpeech()')
  assert await page.locator('#mockCountdown').inner_text()=='02:00';await expire();assert await page.evaluate('(id)=>!USER.mock.ratings[id]',p2id)
  await page.locator('[data-mock-action=next]').click();assert await page.evaluate('(id)=>USER.mock.ratings[id].level',p2id)=='unrated'
  while not await page.evaluate('USER.mock.active.partComplete'):
   prompt=await page.evaluate('USER.mock.active.steps[USER.mock.active.index].prompt');await page.locator('[data-mock-action=resume]').click();assert await page.evaluate('__utterances.at(-1).text')==prompt;await page.evaluate('__endSpeech()');await page.locator('[data-mock-action=next]').click()
  assert await page.locator('[data-mock-part=p2]').count()==1
  await page.locator('[data-mock-action=next-part]').click();assert await page.locator('.mock-exam-row').count()==counts['p3']
  # Voice failure is explicit and does not silently start the answer clock.
  await page.evaluate("window.__voiceMode='error'");await page.locator('[data-mock-action=resume]').click();assert not await page.evaluate('USER.mock.active.running')
  assert '播放失败' in await page.locator('#mockTimerStatus').inner_text();await page.locator('[data-mock-action=manual]').click();assert await page.evaluate('USER.mock.active.running');await expire();await page.locator('[data-mock-action=next]').click();await page.evaluate("window.__voiceMode='manual'")
  # Unsupported browser speech has the same safe manual fallback.
  await page.evaluate("Object.defineProperty(window,'speechSynthesis',{value:undefined,configurable:true})");await page.locator('[data-mock-action=resume]').click();assert '不支持' in await page.locator('#mockTimerStatus').inner_text();assert not await page.evaluate('USER.mock.active.running')
  await page.locator('[data-mock-action=manual]').click();await page.locator('[data-mock-action=next]').click();await page.evaluate("Object.defineProperty(window,'speechSynthesis',{value:__testSynth,configurable:true})")
  while not await page.evaluate('USER.mock.active.partComplete'):await complete_current()
  assert await page.evaluate('USER.mock.active.status')=='exam' and await page.locator('[data-mock-part=p3]').count()==1
  await page.locator('[data-mock-action=next-part]').click();assert await page.evaluate('USER.mock.active.complete')
  attempted=await page.evaluate("USER.mock.active.results.filter(x=>x.outcome==='answered').length")
  assert await page.locator('[data-mock-action=grade]').count()==attempted*3
  await page.locator(f'[data-mock-action=grade][data-id="{first}"][data-level=unfamiliar]').click();assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',first)==0
  await page.locator(f'[data-mock-action=grade][data-id="{p2id}"][data-level=fluent]').click();assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',p2id)==2
  await page.locator('[data-mock-action=archive]').click();assert await page.evaluate('USER.mock.history.length')==1
  await page.locator('.mock-history').first.evaluate('(n)=>{for(let p=n;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true}')
  await page.locator(f'[data-mock-action=grade][data-id="{p2id}"][data-level=unfamiliar]').click();assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',p2id)==0
  # Export a partly finished Part with an interrupted voice, then restore it.
  await page.locator('[data-mock-action=begin]').click();await page.locator('[data-mock-action=resume]').click();await complete_current();await page.locator('[data-mock-action=resume]').click()
  active_id=await page.evaluate('USER.mock.active.id');await page.locator('.nav [data-page=versions]').click();assert not await page.evaluate('USER.mock.active.running')
  async with page.expect_download() as downloaded:await page.locator('[data-action=export]').click()
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'mock-backup.json';await (await downloaded.value).save_as(path);backup=json.loads(path.read_text());assert backup['user']['mock']['history'][0]['notes']=='setting / change / reflection'
   await page.evaluate('localStorage.removeItem(STORAGE)');await page.reload();await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=versions]').click();await page.locator('#importFile').set_input_files(path)
   await page.wait_for_function("document.getElementById('backupStatus').textContent.includes('已导入')");assert await page.evaluate('USER.mock.active.id')==active_id
   state=await page.evaluate('JSON.stringify(USER.mock)')
   legacy={'schema':'IELTS-SPEAKING-BACKUP-v1','version':'1.3.1','user':{'drafts':{'p1-02-1':'legacy note survives'}}}
   await page.locator('#importFile').set_input_files({'name':'legacy.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()});await page.wait_for_function("USER.drafts['p1-02-1']==='legacy note survives'");assert await page.evaluate('JSON.stringify(USER.mock)')==state
   older=json.loads(json.dumps(backup));oldactive=older['user']['mock']['active']
   for key in ['stepResults','stepStarted','voiceRead','partComplete']:oldactive.pop(key,None)
   await page.locator('#importFile').set_input_files({'name':'old-mock.json','mimeType':'application/json','buffer':json.dumps(older).encode()});await page.wait_for_function('USER.mock.active.stepResults.length===1');assert await page.evaluate('USER.mock.active.results.length')==1
   bad={'schema':'IELTS-SPEAKING-BACKUP-v1','user':{'drafts':{'tampered':'bad'},'mock':{'schema':1,'ratings':{'unknown-question':{'level':'fluent','attempts':1,'at':0}},'history':[],'active':None}}}
   await page.locator('#importFile').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(bad).encode()});await page.wait_for_function("document.getElementById('backupStatus').textContent.includes('导入失败')");assert not await page.evaluate("'tampered' in USER.drafts")
  await page.locator('.nav [data-page=mock]').click();assert await page.locator('.mock-exam-row').count()>=10
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  await page.screenshot(path='/workspace/work/speaking/mock-parts/mobile-part.png',full_page=True)
  await page.locator('[data-mock-action=finish]').click();assert not await page.evaluate('USER.mock.active.complete');await page.locator('[data-mock-action=archive]').click()
  assert not errors,errors;await browser.close();print(json.dumps({'planned':counts,'attempted':attempted,'whole_part_display':'passed','zero_never_advances':'passed','explicit_part_transitions':'passed','speech_before_timer':'passed','voice_errors_and_stale_callbacks':'passed','legacy_resume_backup':'passed','self_rating_recycle':'passed','mobile':'passed','errors':errors}))
asyncio.run(main())

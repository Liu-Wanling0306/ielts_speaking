"""Exercise timed exam, no-spoiler stages, self-rating, resume and backup compatibility."""
import asyncio,json,os,shutil,tempfile
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None)
  page=await browser.new_page(viewport={'width':1440,'height':1000},ignore_https_errors=True);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(os.environ.get('SPEAKING_TEST_URL','http://127.0.0.1:8001'));await page.wait_for_selector('#content h2')
  await page.locator('.nav [data-page=mock]').click();assert await page.locator('.mock-pool').count()==3
  await page.locator('[data-mock-action=begin]').click();assert '身份确认' in await page.locator('#mockExamPanel').inner_text()
  assert await page.evaluate('Object.keys(USER.mock.ratings).length')==0
  plan_id=await page.evaluate('USER.mock.active.id')
  counts=await page.evaluate("Object.fromEntries(['p1','p2','p3','wrap'].map(k=>[k,USER.mock.active.steps.filter(s=>s.kind===k).length]))")
  assert 10<=counts['p1']<=12 and 4<=counts['p3']<=6 and counts['p2']==1 and counts['wrap']==2
  await page.locator('[data-mock-action=resume]').click()
  first=await page.evaluate('USER.mock.active.steps[USER.mock.active.index].qid')
  assert await page.locator('.reference').count()==0
  await page.locator('[data-mock-action=pause]').click();paused=await page.locator('#mockCountdown').inner_text();await page.wait_for_timeout(300);assert paused==await page.locator('#mockCountdown').inner_text()
  assert await page.evaluate('Object.keys(USER.mock.ratings).length')==0
  await page.locator('[data-mock-action=next]').click();assert await page.evaluate('(id)=>USER.mock.ratings[id].level',first)=='unrated'
  second=await page.evaluate('USER.mock.active.steps[USER.mock.active.index].qid')
  await page.locator('.nav [data-page=p1]').click();assert not await page.evaluate('USER.mock.active.running')
  index=await page.evaluate('USER.mock.active.index');remaining=await page.evaluate('USER.mock.active.remainingMs')
  await page.reload();await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=mock]').click()
  assert await page.evaluate('USER.mock.active.id')==plan_id and await page.evaluate('USER.mock.active.index')==index
  assert abs(await page.evaluate('USER.mock.active.remainingMs')-remaining)<100 and not await page.evaluate('USER.mock.active.running')
  await page.locator('[data-mock-action=resume]').click();await page.locator('[data-mock-action=skip]').click()
  assert await page.evaluate('(id)=>!USER.mock.ratings[id]',second)
  assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',second)==0
  while await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='p1':await page.locator('[data-mock-action=next]').click()
  assert await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='prep'
  p2id=await page.evaluate('USER.mock.active.part2Id');assert await page.evaluate('(id)=>!USER.mock.ratings[id]',p2id)
  await page.locator('#mockNotes').fill('one real story / setting / change / reflection')
  await page.locator('[data-mock-action=pause]').click();await page.reload();await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=mock]').click()
  assert await page.locator('#mockNotes').input_value()=='one real story / setting / change / reflection'
  assert not await page.evaluate('USER.mock.active.running')
  async def expire():
   before=await page.evaluate('USER.mock.active.index')
   if not await page.evaluate('USER.mock.active.running'):await page.locator('[data-mock-action=resume]').click()
   await page.evaluate('USER.mock.active.remainingMs=10;USER.mock.active.tickAt=Date.now()-30')
   await page.wait_for_function('(i)=>USER.mock.active.status==="review"||USER.mock.active.index>i',arg=before)
  await expire();assert await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='p2'
  assert '02:00'==await page.locator('#mockCountdown').inner_text()
  assert await page.locator('.reference').count()==0
  await expire();assert await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='wrap'
  assert await page.evaluate('(id)=>USER.mock.ratings[id].level',p2id)=='unrated'
  await expire();await expire();assert await page.evaluate("USER.mock.active.steps[USER.mock.active.index].kind")=='p3'
  await expire()
  while await page.evaluate('USER.mock.active.status')=='exam':await page.locator('[data-mock-action=next]').click()
  assert await page.evaluate('USER.mock.active.complete')
  completed=await page.evaluate("USER.mock.active.results.filter(x=>x.outcome==='answered').length")
  assert await page.locator('[data-mock-action=grade]').count()==completed*3
  await page.locator(f'[data-mock-action=grade][data-id="{first}"][data-level=unfamiliar]').click()
  assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',first)==0
  await page.locator(f'[data-mock-action=grade][data-id="{p2id}"][data-level=fluent]').click()
  assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',p2id)==2
  other=await page.evaluate('(first)=>USER.mock.active.results.find(x=>x.outcome==="answered"&&x.id!==first&&x.id!==USER.mock.active.part2Id).id',first)
  await page.locator(f'[data-mock-action=grade][data-id="{other}"][data-level=developing]').click()
  assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',other)==1
  await page.locator('[data-mock-action=archive]').click();assert await page.evaluate('USER.mock.history.length')==1
  assert await page.evaluate('USER.mock.active') is None
  # Historical self-rating also recycles a question, without creating a new attempt.
  await page.locator('.mock-history').first.evaluate('(n)=>{for(let p=n;p;p=p.parentElement)if(p.tagName==="DETAILS")p.open=true}')
  await page.locator(f'[data-mock-action=grade][data-id="{p2id}"][data-level=unfamiliar]').click()
  assert await page.evaluate('(id)=>SpeakingMockCore.tier(MOCK_EXAM.bank.alias.get(id),USER)',p2id)==0
  await page.locator('[data-mock-action=begin]').click();await page.locator('[data-mock-action=resume]').click();await page.locator('[data-mock-action=next]').click();await page.locator('[data-mock-action=pause]').click()
  active_id=await page.evaluate('USER.mock.active.id')
  await page.locator('.nav [data-page=versions]').click()
  async with page.expect_download() as downloaded:await page.locator('[data-action=export]').click()
  with tempfile.TemporaryDirectory() as directory:
   path=Path(directory)/'mock-backup.json';await (await downloaded.value).save_as(path);backup=json.loads(path.read_text());assert backup['user']['mock']['history'][0]['id']==plan_id
   assert backup['user']['mock']['history'][0]['notes']=='one real story / setting / change / reflection'
   await page.evaluate('localStorage.removeItem(STORAGE)');await page.reload();await page.wait_for_selector('#content h2');await page.locator('.nav [data-page=versions]').click();await page.locator('#importFile').set_input_files(path)
   await page.wait_for_function("document.getElementById('backupStatus').textContent.includes('已导入')")
   assert await page.evaluate('USER.mock.active.id')==active_id and await page.evaluate('USER.mock.history.length')==1
   assert not await page.evaluate('USER.mock.active.running')
   state=await page.evaluate('JSON.stringify(USER.mock)')
   legacy={'schema':'IELTS-SPEAKING-BACKUP-v1','version':'1.3.1','user':{'drafts':{'p1-02-1':'legacy note survives'}}}
   await page.locator('#importFile').set_input_files({'name':'legacy.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()});await page.wait_for_function("USER.drafts['p1-02-1']==='legacy note survives'")
   assert await page.evaluate('JSON.stringify(USER.mock)')==state
   bad={'schema':'IELTS-SPEAKING-BACKUP-v1','user':{'drafts':{'tampered':'bad'},'mock':{'schema':1,'ratings':{'unknown-question':{'level':'fluent','attempts':1,'at':0}},'history':[],'active':None}}}
   await page.locator('#importFile').set_input_files({'name':'bad.json','mimeType':'application/json','buffer':json.dumps(bad).encode()});await page.wait_for_function("document.getElementById('backupStatus').textContent.includes('导入失败')")
   assert not await page.evaluate("'tampered' in USER.drafts")
  await page.locator('.nav [data-page=mock]').click();await page.set_viewport_size({'width':390,'height':844})
  assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  await page.screenshot(path='/workspace/work/speaking/mock/mobile-active.png',full_page=True)
  await page.locator('[data-mock-action=finish]').click();assert not await page.evaluate('USER.mock.active.complete')
  assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  await page.locator('[data-mock-action=archive]').click();assert await page.evaluate('USER.mock.history.length')==2
  assert not errors,errors
  await browser.close();print(json.dumps({'planned':counts,'attempted':completed,'timer_auto_advance':'passed','no_spoilers':'passed','pause_reload_notes':'passed','unfamiliar_recycling':'passed','history_and_backup':'passed','legacy_atomic_import':'passed','mobile':'passed','errors':errors}))
asyncio.run(main())

"""Browser regression tests. Start local server; optionally set SPEAKING_TEST_URL."""
import asyncio,json,os,shutil,tempfile
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  browser=await p.chromium.launch(headless=True,executable_path=shutil.which('chromium') or None)
  page=await browser.new_page(viewport={'width':1440,'height':1050},ignore_https_errors=True);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  await page.goto(os.environ.get('SPEAKING_TEST_URL','http://127.0.0.1:8001'))
  await page.wait_for_selector('#content h2')
  assert await page.locator('#loadStatus').is_hidden()
  assert '13' in await page.locator('.stats').inner_text()
  # Exercise all source groups and every learning mode, without changing content.
  await page.locator('.nav button[data-page=p2]').click()
  result=await page.evaluate('''() => {
   let cards=0,clozes=0;
   for(const g of LIB.groups){
    state.group=g.id;
    for(const mode of ['read','cloze','retell','transfer']){
     state.mode=mode;render();
     if(document.querySelectorAll('.legend input').length!==4)throw Error('Missing legend');
     if(mode==='read'&&!document.querySelector('.reference .en').textContent)throw Error('Missing mother material');
     if(mode==='cloze'){const n=document.querySelectorAll('[data-answer-key]').length;if(n!==g.phrases.length)throw Error('Missing phrase exercise');clozes+=n}
     if(mode==='retell'&&!document.querySelector('[data-draft="mother:'+g.id+'"]'))throw Error('Missing retell draft');
     if(mode==='transfer'){
      const nodes=[...document.querySelectorAll('.exercise[id^=card-]')];
      if(nodes.length!==groupCards(g).length)throw Error('Missing transfer cards');
      nodes.forEach(n=>{if(![4,5].includes(n.querySelectorAll('.cue li').length))throw Error('Incomplete cue');if(n.querySelector('.reference').open)throw Error('Answer should start hidden')});cards+=nodes.length;
     }
    }
   }
   state.group='story-a';state.mode='transfer';render();return {groups:LIB.groups.length,transfer_cards:cards,phrase_exercises:clozes};
  }''')
  first=page.locator('.exercise[id^=card-]').first
  await first.locator('textarea').fill('saved personal speaking notes')
  await first.locator('input[data-complete]').check()
  await first.locator('button[data-action=review]').click()
  assert await first.locator('.reference').first.evaluate('(d)=>!d.open')
  await first.locator('.reference > summary').first.click()
  assert await first.locator('.reference').first.evaluate('(d)=>d.open')
  # Highlight preferences, timer controls and navigation are functional.
  await page.locator('[data-highlight=story]').uncheck()
  assert await page.locator('mark[data-kind=story]').count()==0
  await page.locator('[data-highlight=story]').check()
  await page.locator('[data-action=clock-duration][data-seconds="60"]').click()
  assert await page.locator('#timerDisplay').inner_text()=='01:00'
  await page.locator('#clockToggle').click();assert await page.locator('#clockToggle').inner_text()=='暂停'
  await page.locator('#clockToggle').click();assert await page.locator('#clockToggle').inner_text()=='开始计时'
  await page.locator('[data-action=clock-reset]').click()
  # Check exact-match cloze feedback and persistence.
  await page.locator('[data-action=mode][data-mode=cloze]').click()
  input=page.locator('[data-answer-key]').first;expected=await input.get_attribute('data-expected')
  await input.fill(expected);await page.locator('[data-action=check-vocab]').first.click()
  assert await input.evaluate('(e)=>e.classList.contains("ok")')
  # Filter groups without resetting the search input.
  await page.locator('#groupSearch').fill('Ning')
  assert await page.locator('[data-group-item]:visible').count()==1
  await page.locator('#groupSearch').fill('不存在的关键词')
  assert '0' in await page.locator('#groupSearchResult').inner_text()
  await page.reload();await page.wait_for_selector('#content h2')
  await page.locator('.nav [data-page=p2]').click();await page.locator('[data-action=mode][data-mode=transfer]').click()
  first=page.locator('.exercise[id^=card-]').first
  assert await first.locator('textarea').input_value()=='saved personal speaking notes'
  assert await first.locator('[data-complete]').is_checked()
  assert '待复习' in await first.locator('[data-action=review]').inner_text()
  # P1 all source and forecast questions; searches show valid groups.
  await page.locator('.nav [data-page=p1]').click()
  assert await page.locator('[data-draft]').count()==119
  await page.locator('#p1Search').fill('hometown');assert await page.locator('[data-filter-item]:visible').count()>=1
  await page.locator('.nav [data-page=p3]').click();assert await page.locator('[data-draft]').count()==162
  await page.locator('#p3Search').fill('camera lens');assert await page.locator('[data-filter-item]:visible').count()>=1
  await page.locator('.nav [data-page=audit]').click()
  assert await page.locator('.audit-row').count()==263
  await page.locator('#auditSearch').fill('film that made you laugh')
  assert await page.locator('.audit-row:visible').count()==1
  # Jump directly to a newly added cue card; its original-source cue is complete.
  await page.evaluate("document.querySelector('[data-action=open-question][data-id=p2-pdf-film]').click()")
  assert await page.locator('#card-p2-pdf-film').is_visible()
  assert 'Xia Luo' in await page.locator('#card-p2-pdf-film .reference .en').text_content()
  await page.locator('.nav [data-page=p1]').click()
  assert await page.locator('#timerDisplay').inner_text()=='00:30'
  assert await page.locator('.model-info').count()==119
  await page.locator('#speechRate').select_option('140')
  assert '140' in await page.locator('.model-info').first.inner_text()
  await page.locator('#speechRate').select_option('120')
  await page.locator('.nav [data-page=p3]').click()
  assert await page.locator('.model-info').count()==162
  # Review routes back to the exact pending transfer question.
  await page.locator('.nav [data-page=review]').click();assert 'conversation' in await page.locator('#content').inner_text()
  await page.locator('[data-action=open-question]').first.click();assert await page.locator('#card-p2-01').is_visible()
  # Include a personal correction in backup; clear data and restore.
  await page.locator('.nav [data-page=review]').click()
  await page.locator('#wrong').fill('my sample error');await page.locator('#correct').fill('my correction');await page.locator('#why').fill('test explanation');await page.locator('#addErrorForm button').click()
  await page.locator('.nav [data-page=versions]').click()
  assert '预测' in await page.locator('#releaseDiff').inner_text()
  async with page.expect_download() as dl:await page.locator('[data-action=export]').click()
  with tempfile.TemporaryDirectory() as tmp:
   file=Path(tmp)/'backup.json';await (await dl.value).save_as(file)
   saved=json.loads(file.read_text());assert saved['user']['drafts']['p2-01']=='saved personal speaking notes'
   assert saved['user']['extraErrors'][-1][0]=='my sample error'
   await page.evaluate('localStorage.removeItem(STORAGE)');await page.reload();await page.wait_for_selector('#content h2')
   await page.locator('.nav [data-page=versions]').click();await page.locator('#importFile').set_input_files(file)
   await page.wait_for_function("document.getElementById('backupStatus').textContent.includes('已导入')")
   assert await page.evaluate("USER.drafts['p2-01']")=='saved personal speaking notes'
   assert await page.evaluate("USER.completed['p2-01']")
   assert await page.evaluate("USER.extraErrors.length")==1
  # Import a legacy v1.0 backup with original Part 1/3 IDs after the expanded-data upgrade.
  legacy={'schema':'IELTS-SPEAKING-BACKUP-v1','version':'1.0.0','user':{'drafts':{'p1-02-1':'legacy hometown note'},'completed':{'p3-01-1':True}}}
  await page.locator('#importFile').set_input_files({'name':'legacy.json','mimeType':'application/json','buffer':json.dumps(legacy).encode()})
  await page.wait_for_function("USER.drafts['p1-02-1']==='legacy hometown note'")
  await page.locator('.nav [data-page=p1]').click()
  assert await page.locator('[data-draft="p1-02-1"]').input_value()=='legacy hometown note'
  await page.locator('.nav [data-page=p3]').click()
  assert await page.locator('[data-complete="p3-01-1"]').is_checked()
  # Data provenance: original 29 answers and pending geographical-invention question retained.
  await page.evaluate("state.group='story-b';state.mode='transfer';go('p2')")
  assert any('待核题' in x for x in await page.locator('#card-p2-20 .note').all_text_contents())
  await page.screenshot(path='/workspace/work/speaking/desktop.png',full_page=True)
  await page.set_viewport_size({'width':390,'height':844})
  for route in ['home','p1','p2','p3','audit','phrases','review','versions']:
   await page.evaluate('(route)=>go(route)',route)
   assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth'),route+' mobile overflow'
  await page.evaluate("state.group='story-a';state.mode='read';go('p2')")
  await page.screenshot(path='/workspace/work/speaking/mobile.png',full_page=True)
  assert not errors,errors
  print(json.dumps({**result,'source_answers':'preserved','draft_progress_review':'passed','timer_and_highlights':'passed','backup_restore':'passed','mobile_all_pages':'passed','page_errors':errors}))
  await browser.close()
asyncio.run(main())

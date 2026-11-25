import asyncio,json,os,shutil,tempfile
from pathlib import Path
from playwright.async_api import async_playwright
async def main():
 async with async_playwright() as p:
  b=await p.chromium.launch(headless=True,executable_path=shutil.which('chromium'));page=await b.new_page(ignore_https_errors=True)
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)));await page.goto(os.getenv('SPEAKING_TEST_URL','http://127.0.0.1:8030'));await page.wait_for_selector('#content h2')
  await page.get_by_role('button',name='考前冲刺',exact=True).click()
  seen=set()
  for day in ['2026-11-25','2026-11-26','2026-11-27','2026-11-28']:
   await page.locator(f'[data-sprint-day="{day}"]').click();assert await page.locator('.sprint-question').count()>0
   ids=await page.locator('[data-sprint-id]').evaluate_all('(ns)=>ns.map(n=>n.dataset.sprintId)');seen.update(ids)
   assert len(ids)==len(set(ids))
   if day.endswith('27'):assert len(ids)==15
  assert len([x for x in seen if x.startswith('sprint-p1')])==36
  assert len([x for x in seen if x.startswith('sprint-p2')])==17
  assert len([x for x in seen if x.startswith('sprint-p3')])==8
  await page.locator('[data-sprint-day="2026-11-25"]').click();field=page.locator('.sprint-question textarea').first;await field.fill('real story details')
  checkbox=page.locator('.sprint-question [data-complete]').first;await checkbox.check();await page.wait_for_function("document.querySelector('#sprintProgress').textContent.includes('1/')")
  await page.locator('.sprint-question .review-button').first.click()
  await page.locator('[data-sprint-day="2026-11-27"]').click();mock=await page.evaluate("USER.answers['sprint:mock:2026-11-27']")
  await page.reload();await page.wait_for_selector('#content h2');await page.evaluate("go('sprint');state.sprintDay='2026-11-25';render()")
  assert await page.locator('.sprint-question textarea').first.input_value()=='real story details'
  assert await page.evaluate("USER.answers['sprint:mock:2026-11-27']")==mock
  await page.evaluate("USER.review['p2-01']=true;save();state.sprintDay='2026-11-28';render()")
  assert await page.locator('[data-sprint-id="p2-01"]').count()==1
  await page.set_viewport_size({'width':390,'height':844});assert await page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  assert not errors,errors
  print('PASS: four daily lists, all61 teaching prompts, stable mock, drafts, completion, dynamic review, mobile')
  await b.close()
asyncio.run(main())

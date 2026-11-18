# IELTS Speaking Lab

固定网站：https://liu-wanling0306.github.io/ielts_speaking/
唯一正式仓库：https://github.com/Liu-Wanling0306/ielts_speaking
当前版本：**1.1.0**

个人口语训练网站；Band 7.5是目标，不是官方评分。已依据本轮上传的73页预测PDF逐题核对；预测来源与校订方法见网页“预测覆盖核查”。训练补充题与预测原题分别标注。

## 学习结构

- Part 1：PDF 24话题105问；另保留14道旧拓展题，共119问。23条原始不同回答保留，13条完全重复项合并。
- Part 2：13个母素材单元，保留29道原文件题，补齐2道PDF漏题，并保留8道明确标注的迁移题，共39题。母素材 → 搭配回忆 → 口头复述 → 换题迁移。
- Part 3：PDF 26组129问；另保留33道旧拓展题，共162问，37条原回答均保留。
- 四色标注：故事线索、搭配、时态线索、第三人称单数；标注只提示部分明确结构。
- 草稿、搭配答案、进度、复习标记和个人错误保存在浏览器localStorage；通过JSON导出和导入跨设备搬运，不自动云同步。
- 计时仅计时，不录音、不识别语音、不自动打分。

## 文件

| 路径 | 作用 |
|---|---|
| `index.html` | 固定入口及数据加载 |
| `app.js` / `app.css` | 训练交互与样式 |
| `data/library.json` | 资料、稳定ID、母素材映射、题卡、原回答与训练参考 |
| `data/releases.json` | 按时间排列的版本与功能清单 |
| `CHANGELOG.md` | 可读更新记录 |
| `source/original-upload.html` | 不修改的上传原文件存档 |
| `check.py` | 原文保留、索引、分组、题卡和版本检查 |
| `tests/verify_ui.py` | 浏览器交互与备份恢复检查 |

## 本地预览与检查

```bash
python3 -m http.server 8001 --bind 127.0.0.1
```

打开 http://127.0.0.1:8001 ，不要直接双击HTML，因为浏览器会限制加载JSON。

```bash
python3 check.py
node --check app.js
python3 tests/verify_ui.py
```

浏览器测试需要安装Playwright及Chromium。可用`SPEAKING_TEST_URL`指定测试地址。

## 更新发布

1. 检查Git状态，保护未提交改动，再`git pull --ff-only`。
2. 沿用稳定内容ID和`ieltsSpeaking:user:v1`存储键；不得重编号已有题目。
3. 新增内容标注来源；原文与改写分开，不虚构个人经历。
4. 同步`library.json`、`releases.json`、页面资源版本参数、README和CHANGELOG。
5. 运行相关检查和浏览器测试，确认旧草稿可恢复。
6. 审查差异，提交，推送`main`；重要发布建立对应Git标签。
7. 等待GitHub Pages构建成功，并打开网站核验本次提交、版本与功能。

GitHub Pages发布来源：`main`分支根目录。不要将令牌或其他凭据写入仓库。


## 1.1.0 预测核查

上传的73页预测PDF经扫描转录与校订，对应 Part 1 24话题/105问、Part 2 29题卡、Part 3 26组/129问。另保留原HTML拓展题与8道迁移题，总计119道Part 1、39道Part 2、162道Part 3。题干覆盖与个人参考准备状态分开显示。

- `data/forecast-audit.json` 保存逐题ID、PDF页码、映射与源文件SHA-256；不公开整份上传PDF。
- 扩写放在 `reference`，原 `answer` 不变；方括号是真实信息待填项。
- 默认120词/分钟估算，可切换语速。时长为训练目标，实际以录音为准。
- 姓名核验例外；事实题按题意客观回答。评分标准依据 IELTS 官方口语评分描述，本站不自动评分或保证Band。
- 《夏洛特烦恼》采用用户本轮补充素材；主角用Xia Luo，观影时间/同伴仍需填写。西湖采用已知咖啡馆经历与UNESCO背景资料。

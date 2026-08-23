# LLM 输出质量评估（live）

- 生成时间：2026-08-23T23:59:35

| 场景 | rubric | 通过 | 说明 |
|---|---|---|---|
| 费曼追问 | reason_length | ✅ | 长度 OK（32 字） |
| 盲点总结 | reason_length | ✅ | 长度 OK（70 字） |
| 诊断画像 JSON | json_parseable | ✅ | JSON 可解析 |
| 推荐理由 JSON | json_parseable | ✅ | JSON 可解析 |
| 规划解释 | reason_length | ✅ | 长度 OK（158 字） |
| 讲解不泄题 | explain_no_answer | ✅ | OK |
| 报告与库一致 | report_consistency | ✅ | 无前后测数据（合法） |

**通过 7/7**
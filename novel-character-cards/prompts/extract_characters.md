# Character Extraction Prompt

Use this prompt when replacing the heuristic extractor with a real LLM call.

## Task

Read the provided novel chunk and extract character information as structured JSON.

## Requirements

- Focus on actual characters, not locations or organizations.
- Merge obvious aliases in the same chunk.
- Keep unsupported claims out.
- Include short evidence snippets from the source chunk.
- If a field is unknown, omit it instead of guessing.

## Target JSON Shape

```json
{
  "chunk_id": "chunk-0001",
  "characters": [
    {
      "name": "安格列",
      "aliases": ["安格列·里奥"],
      "identity": "乡下贵族次子",
      "faction": "",
      "status": "登场",
      "first_appearance": "第001章 穿越",
      "summary": "乡下贵族次子，故事前期的核心人物。",
      "appearance": [],
      "personality": ["冷静", "谨慎"],
      "abilities": [],
      "equipment": [],
      "relationships": [
        {
          "target": "宋野",
          "type": "同一身体中的前后身份"
        }
      ],
      "timeline": [
        {
          "stage": "早期",
          "event": "在马车中醒来，确认自己穿越到异世界。"
        }
      ],
      "evidence": [
        "这是一个名叫安格列·里奥的乡下贵族次子"
      ],
      "mention_count": 3
    }
  ]
}
```

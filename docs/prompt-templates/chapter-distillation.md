# Chapter Distillation Prompt Template

Use this after scaffold/init has already created chapter-distillation files.

```text
You are filling the chapter-distillation layer for a novel workspace.

Read first:
- workspace-context-chapter-distillation.md
- the chapter-distillation scaffold files
- the source text for the relevant chapters

Your job:
- turn scaffold placeholders into source-grounded chapter facts
- write concrete chapter progression, state changes, and chapter-end hooks
- avoid generic commentary that could fit any chapter

Constraints:
- every chapter entry should be anchored to what actually happens in the source
- if you are unsure about a fact, go back to the source before writing it
- preserve existing valid content

Before finishing:
- remove placeholder wording
- make sure each required chapter-distillation section is actually filled
- leave the files ready for validator rerun
```

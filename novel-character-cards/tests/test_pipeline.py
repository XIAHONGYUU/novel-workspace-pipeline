import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from novel_character_cards.chunker import chunk_text
from novel_character_cards.chunker import Chunk
from novel_character_cards.extractor import heuristic_extract
from novel_character_cards.focus_tracker import build_focus_reports
from novel_character_cards.merger import merge_extractions
from novel_character_cards.renderer import render_cards


class PipelineTests(unittest.TestCase):
    def test_chunk_text_splits_chapters(self) -> None:
        text = "序章\n内容\n第001章 开始\n甲出现\n第002章 继续\n乙出现"
        chunks = chunk_text(text, max_chars=1000)
        self.assertEqual(len(chunks), 3)
        self.assertEqual(chunks[1].title, "第001章 开始")

    def test_merge_and_render(self) -> None:
        with TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            extraction_dir = workdir / "extractions"
            extraction_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "chunk_id": "chunk-0001",
                "title": "第001章 开始",
                "characters": [
                    {
                        "name": "安格列",
                        "aliases": [],
                        "summary": "安格列醒了过来",
                        "traits": [],
                        "relationships": [],
                        "evidence": ["安格列醒了过来"],
                        "mention_count": 3,
                    }
                ],
            }
            (extraction_dir / "chunk-0001.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
            merge_extractions(workdir)
            index = render_cards(workdir)
            self.assertTrue(index.exists())
            self.assertIn("安格列", (workdir / "cards" / "安格列.md").read_text(encoding="utf-8"))

    def test_heuristic_extract_filters_noise_variants(self) -> None:
        chunk = Chunk(
            chunk_id="chunk-0001",
            title="第001章 开始",
            start_line=1,
            end_line=6,
            text="\n".join(
                [
                    "安格列从马车上走了下来。",
                    "安格列脸色平静，安格列心里却还在想着刚才的事。",
                    "很快，丽丝佩尔小姐点点头，走了过来。",
                    "安格列看了丽丝佩尔一眼，丽丝佩尔小姐轻声说了几句。",
                ]
            ),
        )

        payload = heuristic_extract(chunk, top_n=10)
        names = {item["name"] for item in payload["characters"]}

        self.assertIn("安格列", names)
        self.assertIn("丽丝佩尔", names)
        self.assertNotIn("安格列脸", names)
        self.assertNotIn("安格列心", names)
        self.assertNotIn("点头", names)
        self.assertNotIn("很快", names)

    def test_merge_extractions_merges_short_prefix_into_longer_name(self) -> None:
        with TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            extraction_dir = workdir / "extractions"
            extraction_dir.mkdir(parents=True, exist_ok=True)
            payload = {
                "chunk_id": "chunk-0001",
                "title": "第001章 开始",
                "characters": [
                    {
                        "name": "奥迪斯",
                        "aliases": [],
                        "identity": "",
                        "faction": "",
                        "status": "登场",
                        "first_appearance": "第001章 开始",
                        "summary": "奥迪斯骑士走了进来",
                        "appearance": [],
                        "personality": [],
                        "abilities": [],
                        "equipment": [],
                        "relationships": [],
                        "timeline": [],
                        "evidence": ["奥迪斯骑士走了进来"],
                        "mention_count": 7,
                    },
                    {
                        "name": "奥迪",
                        "aliases": [],
                        "identity": "",
                        "faction": "",
                        "status": "登场",
                        "first_appearance": "第001章 开始",
                        "summary": "奥迪斯骑士走了进来",
                        "appearance": [],
                        "personality": [],
                        "abilities": [],
                        "equipment": [],
                        "relationships": [],
                        "timeline": [],
                        "evidence": ["奥迪斯骑士走了进来"],
                        "mention_count": 5,
                    },
                ],
            }
            (extraction_dir / "chunk-0001.json").write_text(
                json.dumps(payload, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

            merged_path = merge_extractions(workdir)
            merged = json.loads(merged_path.read_text(encoding="utf-8"))

            self.assertEqual(len(merged), 1)
            self.assertEqual(merged[0]["name"], "奥迪斯")
            self.assertIn("奥迪", merged[0]["aliases"])
            self.assertEqual(merged[0]["mention_count"], 12)

    def test_build_focus_reports_creates_checkpoints(self) -> None:
        with TemporaryDirectory() as tmpdir:
            workdir = Path(tmpdir)
            chunks = [
                Chunk("chunk-0001", "第001章 开始", 1, 2, "安格列二少爷醒了过来。凯尔男爵看着安格列。"),
                Chunk("chunk-0002", "第001章 开始", 3, 4, "其他内容。"),
                Chunk("chunk-0003", "第002章 继续", 5, 6, "安格列看向窗外，安格也没有说话。"),
            ]

            report_path = build_focus_reports(
                chunks,
                workdir,
                focus_name="安格列",
                aliases=["安格"],
                summary_interval=2,
            )

            self.assertTrue(report_path.exists())
            self.assertTrue((workdir / "focus" / "checkpoints" / "checkpoint-0002.md").exists())
            self.assertTrue((workdir / "focus" / "checkpoints" / "checkpoint-0003.md").exists())

            manifest = json.loads((workdir / "focus" / "checkpoints.json").read_text(encoding="utf-8"))
            self.assertEqual(len(manifest), 2)
            self.assertEqual(manifest[-1]["mention_count_total"], 4)
            self.assertTrue(any(item["context_entries"] for item in manifest))


if __name__ == "__main__":
    unittest.main()

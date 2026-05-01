import unittest

from text2markdown.converter import convert_text, decode_text_file


class ConverterTests(unittest.TestCase):
    def test_convert_text_creates_heading_and_chapter(self) -> None:
        source = "测试文档\n\n第001章 开始\n第一段"
        result = convert_text(source, title="测试文档", frontmatter=False)
        self.assertIn("# 测试文档", result)
        self.assertIn("## 第001章 开始", result)
        self.assertIn("第一段", result)

    def test_decode_gb18030_file(self) -> None:
        from tempfile import TemporaryDirectory
        from pathlib import Path

        with TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sample.txt"
            path.write_bytes("巫师世界".encode("gb18030"))
            decoded = decode_text_file(path)
            self.assertEqual(decoded.text, "巫师世界")
            self.assertEqual(decoded.encoding, "gb18030")


if __name__ == "__main__":
    unittest.main()

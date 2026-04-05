# text2markdown

A small local CLI that converts `.txt` files into `.md`.

## Features

- auto-detect common text encodings, including `gb18030`
- normalize line endings and blank lines
- turn chapter-style lines into Markdown headings
- optionally add YAML frontmatter

## Usage

```bash
python3 -m text2markdown.cli input.txt
python3 -m text2markdown.cli input.txt -o output.md --frontmatter
python3 -m text2markdown.cli input.txt --title "My Note"
```

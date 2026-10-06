# inbox — 喂与取 two-verb inbox router

A Hermes skill that routes user-dropped links/screenshots/text into an Obsidian inbox, and recalls stored material when the user wants to use it.

## Setup

```bash
cp .env.example .env
# Edit .env — set OBSIDIAN_INBOX to your Obsidian inbox path
source .env  # or add to your shell profile
```

## Structure

- `SKILL.md` — router: 判动词 → 喂/取 → 加载对应 profile
- `profiles/` — one per source: xiaohongshu, wechat, bilibili, x, paper-pdf, image, video

## License

MIT

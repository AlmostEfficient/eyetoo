# eyetoo

A local image tool for your agents. Background removal and upscaling that runs on your machine. Nothing gets uploaded and your files never leave your computer.

It ships as an agent skill, so you don't run it by hand. You install it once, then your agent (Claude Code, Hermes, OpenClaw, etc.) drives it for you.

## What it lets your agent do

- **Remove backgrounds** — local `rembg`, works on single images or whole folders
- **Upscale** — Real-ESRGAN AI super-resolution, with a Pillow/Lanczos fallback if the native binary isn't installed
- **Both at once** — background removal then upscale, in one pass
- Handles `.png .jpg .jpeg .webp .tif .tiff .bmp`, single files or recursive folders

Requires macOS, Python 3.11+, and [`uv`](https://docs.astral.sh/uv/).

## Install it to your agent

```bash
bunx skills add https://github.com/AlmostEfficient/eyetoo.git -g --skill eyetoo --agent '*' -y
```

That installs the skill globally for every agent. The first run grabs the models it needs (rembg's cache, and Real-ESRGAN if you want AI upscaling) — your agent handles that.

## Use it

Just tell your agent what you want:

> "remove the background from this flyer"
> "upscale these screenshots 4x"
> "cut out the background and upscale this, drop it in ~/Desktop"

The skill picks the right command, runs `doctor` to confirm everything's wired up, and hands you the files. Default output lands in `~/eyetoo-output`.

# eyetoo

Remove backgrounds and upscale images, all on your own machine. Nothing gets uploaded anywhere, so your files never leave your computer.

## What you need

- macOS
- Python 3.11+
- `uv`

Don't have `uv`? Grab it:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Get it running

```bash
git clone https://github.com/AlmostEfficient/eyetoo.git
cd eyetoo
uv sync
```

If you want the good AI upscaling (you do), pull in Real-ESRGAN:

```bash
bin/eyetoo install-realesrgan
```

That downloads the portable Real-ESRGAN macOS build into `tools/`. The binary and model files are big, so they're not committed to the repo — that's why you grab them separately.

## The commands

```bash
bin/eyetoo doctor                          # check everything's wired up
bin/eyetoo bg-remove input.jpg -o ./out    # cut out the background
bin/eyetoo upscale input.png -s 4 -o ./out # make it bigger
bin/eyetoo pipeline input.jpg -s 4 -o ./out # both, in order
```

Prefer typing just `eyetoo` from anywhere? Install it as a real command:

```bash
uv tool install .
eyetoo doctor
```

For an installed command, `eyetoo install-realesrgan` stores Real-ESRGAN under `~/.local/share/eyetoo`. If you want the installed command to use a clone-local `tools/` folder instead, point it there:

```bash
export EYETOO_HOME=/path/to/eyetoo
```

## Removing backgrounds

This uses `rembg` locally. First run downloads the model to `~/.u2net` — that's a one-time thing, then it's cached.

Got a whole folder? Point it at the folder:

```bash
bin/eyetoo bg-remove ./images -o ./out
```

## Upscaling

Real-ESRGAN is the one you want — sharp, AI-driven:

```bash
bin/eyetoo upscale input.png --engine realesrgan -s 4 -o ./out
```

By default the engine is `auto`. It tries Real-ESRGAN first, and if it's not installed it falls back to plain Pillow/Lanczos resizing with a bit of sharpening. Not as nice, but it'll always work:

```bash
bin/eyetoo upscale input.png --engine auto -s 4 -o ./out
```

## The pipeline

Background removal, then upscale, in one go:

```bash
bin/eyetoo pipeline input.jpg -s 4 -o ./out
```

Skip `-o` and everything lands in `~/eyetoo-output`.

Folders work too, and nested folders are preserved under the output directory:

```bash
bin/eyetoo pipeline ./images -s 4 -o ./out
```

## What you can throw at it

Single images or whole folders. Folders get walked recursively, picking up:

```text
.png .jpg .jpeg .webp .tif .tiff .bmp
```

## Just ask your agent

There's an agent skill in `skills/eyetoo/SKILL.md`, so you can skip the commands and say what you want — "cut out the background on this flyer" or "upscale these" — and the agent picks the right command, checks everything's wired up, and hands you the files.

Install it globally so it works in any repo, not just this one:

```bash
bunx skills add https://github.com/AlmostEfficient/eyetoo.git -g --skill eyetoo --agent '*' -y
```

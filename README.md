# eyetoo

Local on-demand image pipeline for background removal and upscaling. No cloud processing.

## Requirements

- macOS
- Python 3.11+
- `uv`

Install `uv` if needed:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

## Install

```bash
git clone https://github.com/AlmostEfficient/eyetoo.git
cd eyetoo
uv sync
```

Optional but recommended for AI upscaling:

```bash
bin/install-realesrgan
```

This downloads the portable Real-ESRGAN ncnn-vulkan macOS release into `tools/`. The downloaded binary and model files are intentionally not committed.

## Commands

```bash
bin/eyetoo doctor
bin/eyetoo bg-remove input.jpg -o ./out
bin/eyetoo upscale input.png -s 4 -o ./out
bin/eyetoo pipeline input.jpg -s 4 -o ./out
```

You can also install the console command:

```bash
uv tool install .
eyetoo doctor
```

If you use the installed `eyetoo` command and want it to find a Real-ESRGAN install from a clone, set:

```bash
export EYETOO_HOME=/path/to/eyetoo
```

## Background Removal

Background removal uses `rembg` locally. The first run downloads its model cache to `~/.u2net`.

Batch folders work:

```bash
bin/eyetoo bg-remove ./images -o ./out
```

## Upscaling

The preferred engine is Real-ESRGAN ncnn-vulkan:

```bash
bin/eyetoo upscale input.png --engine realesrgan -s 4 -o ./out
```

The default `--engine auto` tries Real-ESRGAN first and falls back to local Pillow/Lanczos resizing with light sharpening if Real-ESRGAN is unavailable.

```bash
bin/eyetoo upscale input.png --engine auto -s 4 -o ./out
```

## Pipeline

Run background removal followed by upscaling:

```bash
bin/eyetoo pipeline input.jpg -s 4 -o ./out
```

Default output directory:

```bash
~/eyetoo-output
```

## Supported Inputs

Single images and folders are supported. Folder inputs are processed recursively for:

```text
.png .jpg .jpeg .webp .tif .tiff .bmp
```

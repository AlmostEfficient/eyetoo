---
name: "eyetoo"
description: "Use when the user asks to remove image backgrounds, upscale images, or run a local on-demand image processing pipeline with eyetoo. Supports local background removal via rembg and image upscaling via Real-ESRGAN or Pillow fallback, especially for files in PNG, JPG, JPEG, WEBP, TIFF, BMP formats."
---

# eyetoo

Use the local `eyetoo` CLI for image background removal and upscaling. The pipeline is local-only and does not use cloud processing.

## Locate the Repo

Prefer the current repository if it contains `pyproject.toml` with `name = "eyetoo"`. Otherwise, find a clone or ask the user for the path.

If using an installed `eyetoo` command outside the clone, `eyetoo install-realesrgan` stores Real-ESRGAN under `~/.local/share/eyetoo`. Set `EYETOO_HOME` only when you want the installed command to use a clone-local `tools/` folder:

```bash
export EYETOO_HOME=/path/to/eyetoo
```

## Commands

Run commands from the project directory:

```bash
uv sync
bin/eyetoo doctor
bin/eyetoo bg-remove input.jpg -o ./out
bin/eyetoo upscale input.png -s 4 -o ./out
bin/eyetoo pipeline input.jpg -s 4 -o ./out
bin/eyetoo install-realesrgan
```

Use `pipeline` when the user wants both background removal and upscaling. Use `bg-remove` or `upscale` for single-step work.

## Engines

Prefer `--engine auto` unless the user asks for a specific engine. Auto tries Real-ESRGAN first and falls back to Pillow/Lanczos if the native upscaler is unavailable.

Use `--engine realesrgan` when the user specifically needs AI super-resolution and you want failures to be explicit. Use `--engine pillow` only for deterministic local resizing when AI upscale quality is not required.

## Inputs and Outputs

Inputs can be a single image or a folder. Folder inputs are processed recursively for supported image extensions, and nested folders are preserved under the output directory.

The default output directory is:

```bash
~/eyetoo-output
```

Output naming:

- Background removal: `name-bgremoved.png`
- Upscaling: `name-x4.png` for Real-ESRGAN, or `name-x4-lanczos.png` for Pillow
- Pipeline: `name-bgremoved-x4.png`

## Validation

Before relying on the pipeline, run:

```bash
bin/eyetoo doctor
```

Expected healthy state for the full pipeline:

- `rembg: available`
- `Real-ESRGAN: installed`
- `Real-ESRGAN models: installed`

If Real-ESRGAN models are missing, run:

```bash
bin/eyetoo install-realesrgan
```

After processing, verify outputs with `file output.png` or by opening the image when visual quality matters.

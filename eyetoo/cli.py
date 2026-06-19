from __future__ import annotations
import argparse, os, shutil, subprocess, sys
from pathlib import Path
from PIL import Image, ImageFilter

DEFAULT_OUT = Path.home() / "eyetoo-output"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
ROOT = Path(os.environ.get("EYETOO_HOME", Path(__file__).resolve().parents[1])).expanduser()
UPSCALE_DIR = ROOT / "tools/realesrgan-ncnn-vulkan"
UPSCALE_BIN = UPSCALE_DIR / "realesrgan-ncnn-vulkan"
UPSCALE_MODELS = UPSCALE_DIR / "models"
UPSCALE_MODEL_EXTS = {".param", ".bin"}


def ensure_out(p: str | None) -> Path:
    out = Path(p).expanduser() if p else DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    return out


def out_name(inp: Path, out: Path, suffix: str, ext: str = ".png") -> Path:
    return out / f"{inp.stem}{suffix}{ext}"


def bg_remove_one(inp: Path, out: Path, model: str = "u2net") -> Path:
    from rembg import new_session, remove
    session = new_session(model)
    output = out_name(inp, out, "-bgremoved")
    data = inp.read_bytes()
    res = remove(data, session=session)
    output.write_bytes(res)
    return output


def iter_images(path: Path):
    if path.is_file():
        yield path
    else:
        for p in sorted(path.rglob("*")):
            if p.suffix.lower() in IMAGE_EXTS and p.is_file():
                yield p


def bg_cmd(args):
    src = Path(args.input).expanduser()
    out = ensure_out(args.output)
    made = []
    for img in iter_images(src):
        made.append(bg_remove_one(img, out, args.model))
    for p in made: print(p)
    return 0


def upscale_with_realesrgan(inp: Path, out: Path, scale: int, model: str):
    if not UPSCALE_BIN.exists():
        raise FileNotFoundError(f"Real-ESRGAN binary not installed at {UPSCALE_BIN}. Run: bin/eyetoo doctor")
    if not has_realesrgan_models():
        raise FileNotFoundError(f"Real-ESRGAN models not installed at {UPSCALE_MODELS}. Run: bin/install-realesrgan")
    output = out_name(inp, out, f"-x{scale}")
    cmd = [str(UPSCALE_BIN), "-i", str(inp), "-o", str(output), "-n", model, "-s", str(scale), "-m", str(UPSCALE_MODELS)]
    subprocess.run(cmd, check=True)
    return output


def upscale_with_pillow(inp: Path, out: Path, scale: int):
    im = Image.open(inp).convert("RGBA")
    up = im.resize((im.width * scale, im.height * scale), Image.Resampling.LANCZOS)
    # light unsharp mask for logos/print prep, not AI SR
    up = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))
    output = out_name(inp, out, f"-x{scale}-lanczos")
    up.save(output)
    return output


def up_cmd(args):
    src = Path(args.input).expanduser()
    out = ensure_out(args.output)
    made=[]
    for img in iter_images(src):
        if args.engine == "realesrgan": made.append(upscale_with_realesrgan(img, out, args.scale, args.model))
        elif args.engine == "pillow": made.append(upscale_with_pillow(img, out, args.scale))
        else:
            try: made.append(upscale_with_realesrgan(img, out, args.scale, args.model))
            except Exception as e:
                print(f"Real-ESRGAN unavailable ({e}); falling back to Pillow/Lanczos", file=sys.stderr)
                made.append(upscale_with_pillow(img, out, args.scale))
    for p in made: print(p)
    return 0


def pipeline_cmd(args):
    out = ensure_out(args.output)
    tmp = out / ".tmp-bg"
    tmp.mkdir(parents=True, exist_ok=True)
    bg_out = bg_remove_one(Path(args.input).expanduser(), tmp, args.model)
    up_args = argparse.Namespace(input=str(bg_out), output=str(out), scale=args.scale, engine=args.engine, model=args.upscale_model)
    made_rc = up_cmd(up_args)
    if not args.keep_tmp: shutil.rmtree(tmp, ignore_errors=True)
    return made_rc

def has_realesrgan_models() -> bool:
    return UPSCALE_MODELS.exists() and any(
        p.is_file() and p.suffix.lower() in UPSCALE_MODEL_EXTS
        for p in UPSCALE_MODELS.rglob("*")
    )


def doctor_cmd(args):
    print(f"project: {ROOT}")
    print(f"default output: {DEFAULT_OUT}")
    try:
        import rembg  # noqa: F401
        print("rembg: available")
    except Exception as e:
        print(f"rembg: unavailable ({e})")
    if UPSCALE_BIN.exists():
        print(f"Real-ESRGAN: installed at {UPSCALE_BIN}")
        if has_realesrgan_models():
            print(f"Real-ESRGAN models: installed at {UPSCALE_MODELS}")
        else:
            print(f"Real-ESRGAN models: missing at {UPSCALE_MODELS}")
            print("install Real-ESRGAN models: bin/install-realesrgan")
    else:
        print(f"Real-ESRGAN: missing at {UPSCALE_BIN}")
        print("install Real-ESRGAN: bin/install-realesrgan")
    return 0


def main(argv=None):
    p=argparse.ArgumentParser(prog="eyetoo", description="Local image bg removal/upscaling pipeline")
    sub=p.add_subparsers(required=True)
    bg=sub.add_parser("bg-remove", aliases=["bg"]); bg.add_argument("input"); bg.add_argument("-o","--output"); bg.add_argument("--model", default="u2net"); bg.set_defaults(func=bg_cmd)
    up=sub.add_parser("upscale", aliases=["up"]); up.add_argument("input"); up.add_argument("-o","--output"); up.add_argument("-s","--scale", type=int, default=4, choices=[2,3,4]); up.add_argument("--engine", choices=["auto","realesrgan","pillow"], default="auto"); up.add_argument("--model", default="realesrgan-x4plus"); up.set_defaults(func=up_cmd)
    pipe=sub.add_parser("pipeline", aliases=["pipe"]); pipe.add_argument("input"); pipe.add_argument("-o","--output"); pipe.add_argument("-s","--scale", type=int, default=4, choices=[2,3,4]); pipe.add_argument("--model", default="u2net"); pipe.add_argument("--engine", choices=["auto","realesrgan","pillow"], default="auto"); pipe.add_argument("--upscale-model", default="realesrgan-x4plus"); pipe.add_argument("--keep-tmp", action="store_true"); pipe.set_defaults(func=pipeline_cmd)
    d=sub.add_parser("doctor"); d.set_defaults(func=doctor_cmd)
    args=p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__": raise SystemExit(main())

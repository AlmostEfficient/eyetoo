from __future__ import annotations
import argparse, json, os, platform, shutil, subprocess, sys, urllib.request, zipfile
from pathlib import Path
from PIL import Image, ImageFilter

DEFAULT_OUT = Path.home() / "eyetoo-output"
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".webp", ".tif", ".tiff", ".bmp"}
ROOT = Path(os.environ.get("EYETOO_HOME", Path(__file__).resolve().parents[1])).expanduser()
USER_TOOL_ROOT = Path(os.environ.get("XDG_DATA_HOME", Path.home() / ".local/share")) / "eyetoo"
TOOL_ROOT = ROOT if os.environ.get("EYETOO_HOME") or (ROOT / "pyproject.toml").exists() else USER_TOOL_ROOT
UPSCALE_DIR = TOOL_ROOT / "tools/realesrgan-ncnn-vulkan"
UPSCALE_BIN = UPSCALE_DIR / "realesrgan-ncnn-vulkan"
UPSCALE_MODELS = UPSCALE_DIR / "models"
UPSCALE_MODEL_EXTS = {".param", ".bin"}
REALESRGAN_RELEASE_API = "https://api.github.com/repos/xinntao/Real-ESRGAN/releases/tags/v0.2.5.0"
# RMBG-2.0 won a side-by-side against birefnet, isnet, u2net and Apple Vision (cleanest edges, fewest leaks).
# Its weights are CC BY-NC: fine for personal use, swap to birefnet-general (MIT) for commercial work.
DEFAULT_BG_MODEL = "bria-rmbg"
LIFT_SRC = Path(__file__).resolve().parent / "lift.swift"
LIFT_BIN = TOOL_ROOT / "tools/lift/eyetoo-lift"


def ensure_out(p: str | None) -> Path:
    out = Path(p).expanduser() if p else DEFAULT_OUT
    out.mkdir(parents=True, exist_ok=True)
    return out


def out_name(inp: Path, out: Path, suffix: str, ext: str = ".png", rel: Path | None = None) -> Path:
    rel = rel or Path(inp.name)
    target = out / rel.parent / f"{rel.stem}{suffix}{ext}"
    target.parent.mkdir(parents=True, exist_ok=True)
    return target


def ensure_lift() -> Path:
    """Compile the Apple Vision subject-lift helper on first use (and after the source changes)."""
    if LIFT_BIN.exists() and LIFT_BIN.stat().st_mtime >= LIFT_SRC.stat().st_mtime:
        return LIFT_BIN
    if not shutil.which("swiftc"):
        raise FileNotFoundError("--fast needs swiftc (xcode-select --install)")
    LIFT_BIN.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(["swiftc", "-O", str(LIFT_SRC), "-o", str(LIFT_BIN)], check=True)
    return LIFT_BIN


def bg_session(model: str, fast: bool = False):
    """Load the model once per run; callers pass the result to every bg_remove_one call."""
    if fast:
        return ensure_lift()
    from rembg import new_session
    return new_session(model)


def bg_remove_one(inp: Path, out: Path, session, rel: Path | None = None) -> Path:
    output = out_name(inp, out, "-bgremoved", rel=rel)
    if isinstance(session, Path):
        try:
            subprocess.run([str(session), str(inp), str(output)], check=True, timeout=60)
        except subprocess.TimeoutExpired:
            raise RuntimeError("Apple Vision timed out; the Neural Engine is busy (ANECompilerService), drop --fast or retry later")
        return output
    from rembg import remove
    output.write_bytes(remove(inp.read_bytes(), session=session))
    return output


def iter_images(path: Path):
    if path.is_file():
        yield path, Path(path.name)
    else:
        for p in sorted(path.rglob("*")):
            if p.suffix.lower() in IMAGE_EXTS and p.is_file():
                yield p, p.relative_to(path)


def collect_images(path: Path) -> list[tuple[Path, Path]]:
    if not path.exists():
        raise FileNotFoundError(f"input does not exist: {path}")
    if path.is_file() and path.suffix.lower() not in IMAGE_EXTS:
        supported = ", ".join(sorted(IMAGE_EXTS))
        raise ValueError(f"unsupported image type: {path.suffix or '(none)'}; supported: {supported}")
    images = list(iter_images(path))
    if not images:
        raise ValueError(f"no supported images found in: {path}")
    return images


def report_input_error(e: Exception) -> int:
    print(f"eyetoo: {e}", file=sys.stderr)
    return 2


def bg_cmd(args):
    src = Path(args.input).expanduser()
    out = ensure_out(args.output)
    try:
        images = collect_images(src)
    except (FileNotFoundError, ValueError) as e:
        return report_input_error(e)
    session = bg_session(args.model, args.fast)
    made = []
    for img, rel in images:
        made.append(bg_remove_one(img, out, session, rel))
    for p in made: print(p)
    return 0


def upscale_with_realesrgan(inp: Path, out: Path, scale: int, model: str, rel: Path | None = None):
    if not UPSCALE_BIN.exists():
        raise FileNotFoundError(f"Real-ESRGAN binary not installed at {UPSCALE_BIN}. Run: eyetoo install-realesrgan")
    if not has_realesrgan_models():
        raise FileNotFoundError(f"Real-ESRGAN models not installed at {UPSCALE_MODELS}. Run: eyetoo install-realesrgan")
    output = out_name(inp, out, f"-x{scale}", rel=rel)
    cmd = [str(UPSCALE_BIN), "-i", str(inp), "-o", str(output), "-n", model, "-s", str(scale), "-m", str(UPSCALE_MODELS)]
    subprocess.run(cmd, check=True)
    return output


def upscale_with_pillow(inp: Path, out: Path, scale: int, rel: Path | None = None):
    im = Image.open(inp).convert("RGBA")
    up = im.resize((im.width * scale, im.height * scale), Image.Resampling.LANCZOS)
    # light unsharp mask for logos/print prep, not AI SR
    up = up.filter(ImageFilter.UnsharpMask(radius=1.2, percent=110, threshold=3))
    output = out_name(inp, out, f"-x{scale}-lanczos", rel=rel)
    up.save(output)
    return output


def up_cmd(args):
    src = Path(args.input).expanduser()
    out = ensure_out(args.output)
    try:
        images = collect_images(src)
    except (FileNotFoundError, ValueError) as e:
        return report_input_error(e)
    made=[]
    for img, rel in images:
        if args.engine == "realesrgan": made.append(upscale_with_realesrgan(img, out, args.scale, args.model, rel))
        elif args.engine == "pillow": made.append(upscale_with_pillow(img, out, args.scale, rel))
        else:
            try: made.append(upscale_with_realesrgan(img, out, args.scale, args.model, rel))
            except Exception as e:
                print(f"Real-ESRGAN unavailable ({e}); falling back to Pillow/Lanczos", file=sys.stderr)
                made.append(upscale_with_pillow(img, out, args.scale, rel))
    for p in made: print(p)
    return 0


def pipeline_one(inp: Path, rel: Path, out: Path, args, session) -> Path:
    """Remove background into a temp folder, then upscale into the final output."""
    tmp = out / ".tmp-bg"
    tmp.mkdir(parents=True, exist_ok=True)
    bg_out = bg_remove_one(inp, tmp, session, rel)
    bg_rel = rel.parent / f"{rel.stem}-bgremoved.png"
    try:
        if args.engine == "realesrgan":
            return upscale_with_realesrgan(bg_out, out, args.scale, args.upscale_model, bg_rel)
        if args.engine == "pillow":
            return upscale_with_pillow(bg_out, out, args.scale, bg_rel)
        try:
            return upscale_with_realesrgan(bg_out, out, args.scale, args.upscale_model, bg_rel)
        except Exception as e:
            print(f"Real-ESRGAN unavailable ({e}); falling back to Pillow/Lanczos", file=sys.stderr)
            return upscale_with_pillow(bg_out, out, args.scale, bg_rel)
    finally:
        if not args.keep_tmp:
            shutil.rmtree(tmp, ignore_errors=True)


def pipeline_cmd(args):
    src = Path(args.input).expanduser()
    out = ensure_out(args.output)
    try:
        images = collect_images(src)
    except (FileNotFoundError, ValueError) as e:
        return report_input_error(e)
    session = bg_session(args.model, args.fast)
    made = [pipeline_one(img, rel, out, args, session) for img, rel in images]
    for p in made:
        print(p)
    return 0


def realesrgan_download_url() -> str:
    with urllib.request.urlopen(REALESRGAN_RELEASE_API, timeout=30) as response:
        release = json.load(response)
    assets = release.get("assets", [])
    for asset in assets:
        name = asset.get("name", "").lower()
        if name.endswith(".zip") and "ncnn-vulkan" in name and "macos" in name:
            return asset["browser_download_url"]
    available = ", ".join(asset.get("name", "") for asset in assets)
    raise RuntimeError(f"could not find macOS Real-ESRGAN ncnn-vulkan asset; available: {available}")


def install_realesrgan_cmd(args):
    if platform.system().lower() != "darwin":
        print(f"eyetoo: Real-ESRGAN installer currently supports macOS only, got {platform.system()}", file=sys.stderr)
        return 2
    install_root = Path(args.install_root).expanduser() if args.install_root else TOOL_ROOT
    install_dir = install_root / "tools/realesrgan-ncnn-vulkan"
    bin_path = install_dir / "realesrgan-ncnn-vulkan"
    models = install_dir / "models"
    if not args.force and bin_path.exists() and has_realesrgan_models_at(models):
        print(f"already installed: {install_dir}")
        return 0

    import tempfile
    url = realesrgan_download_url()
    print(f"downloading {url}")
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp = Path(tmp_dir)
        archive = tmp / "realesrgan.zip"
        urllib.request.urlretrieve(url, archive)
        unpacked = tmp / "unpacked"
        with zipfile.ZipFile(archive) as zf:
            zf.extractall(unpacked)
        matches = [p for p in unpacked.rglob("realesrgan-ncnn-vulkan") if p.is_file()]
        if not matches:
            raise FileNotFoundError("could not find realesrgan-ncnn-vulkan binary in archive")
        src_dir = matches[0].parent
        if install_dir.exists():
            shutil.rmtree(install_dir)
        install_dir.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(src_dir, install_dir)
        bin_path.chmod(bin_path.stat().st_mode | 0o111)

    if not has_realesrgan_models_at(models):
        raise FileNotFoundError(f"installed binary, but no Real-ESRGAN model files were found at {models}")
    print(f"installed: {install_dir}")
    return 0

def has_realesrgan_models() -> bool:
    return has_realesrgan_models_at(UPSCALE_MODELS)


def has_realesrgan_models_at(models: Path) -> bool:
    return models.exists() and any(
        p.is_file() and p.suffix.lower() in UPSCALE_MODEL_EXTS
        for p in models.rglob("*")
    )


def doctor_cmd(args):
    print(f"project: {ROOT}")
    print(f"tool root: {TOOL_ROOT}")
    print(f"default output: {DEFAULT_OUT}")
    try:
        import rembg  # noqa: F401
        print("rembg: available")
    except Exception as e:
        print(f"rembg: unavailable ({e})")
    print(f"bg model: {DEFAULT_BG_MODEL} (downloads on first use)")
    print(f"fast bg (Apple Vision): {'ready' if LIFT_BIN.exists() else 'compiles on first --fast run' if shutil.which('swiftc') else 'unavailable, needs swiftc'}")
    if UPSCALE_BIN.exists():
        print(f"Real-ESRGAN: installed at {UPSCALE_BIN}")
        if has_realesrgan_models():
            print(f"Real-ESRGAN models: installed at {UPSCALE_MODELS}")
        else:
            print(f"Real-ESRGAN models: missing at {UPSCALE_MODELS}")
            print("install Real-ESRGAN models: eyetoo install-realesrgan")
    else:
        print(f"Real-ESRGAN: missing at {UPSCALE_BIN}")
        print("install Real-ESRGAN: eyetoo install-realesrgan")
    return 0


def main(argv=None):
    p=argparse.ArgumentParser(prog="eyetoo", description="Local image bg removal/upscaling pipeline")
    sub=p.add_subparsers(required=True)
    bg=sub.add_parser("bg-remove", aliases=["bg"]); bg.add_argument("input"); bg.add_argument("-o","--output"); bg.add_argument("--model", default=DEFAULT_BG_MODEL); bg.add_argument("--fast", action="store_true", help="Apple Vision subject lift: ~0.1s/image, rougher hair edges"); bg.set_defaults(func=bg_cmd)
    up=sub.add_parser("upscale", aliases=["up"]); up.add_argument("input"); up.add_argument("-o","--output"); up.add_argument("-s","--scale", type=int, default=4, choices=[2,3,4]); up.add_argument("--engine", choices=["auto","realesrgan","pillow"], default="auto"); up.add_argument("--model", default="realesrgan-x4plus"); up.set_defaults(func=up_cmd)
    pipe=sub.add_parser("pipeline", aliases=["pipe"]); pipe.add_argument("input"); pipe.add_argument("-o","--output"); pipe.add_argument("-s","--scale", type=int, default=4, choices=[2,3,4]); pipe.add_argument("--model", default=DEFAULT_BG_MODEL); pipe.add_argument("--fast", action="store_true"); pipe.add_argument("--engine", choices=["auto","realesrgan","pillow"], default="auto"); pipe.add_argument("--upscale-model", default="realesrgan-x4plus"); pipe.add_argument("--keep-tmp", action="store_true"); pipe.set_defaults(func=pipeline_cmd)
    install=sub.add_parser("install-realesrgan"); install.add_argument("--install-root"); install.add_argument("--force", action="store_true"); install.set_defaults(func=install_realesrgan_cmd)
    d=sub.add_parser("doctor"); d.set_defaults(func=doctor_cmd)
    args=p.parse_args(argv)
    return args.func(args)

if __name__ == "__main__": raise SystemExit(main())

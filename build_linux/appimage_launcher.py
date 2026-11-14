#!/usr/bin/env python3
"""appimage_launcher.py - Standalone AppImage Launcher for ReadAloud.

Detects whether multi-volume data slices (.001 and .002) are present.
If missing, prompts the user via a native GUI (GTK / Zenity / KDialog / Tkinter / CLI)
to automatically download them from GitHub Releases with unified progress reporting.
Assembles the full offline runtime into ~/.local/share/readaloud/ and executes it.
Subsequent launches execute the assembled application instantly.
"""

import os
import sys
import shutil
import urllib.request
import subprocess
from pathlib import Path

VERSION = "1.8.19"
REPO_URL = "https://github.com/Zackarious/ReadAloud"
RELEASE_TAG = f"v{VERSION}"
DOWNLOAD_BASE_URL = f"{REPO_URL}/releases/download/{RELEASE_TAG}"

SLICES = [
    {
        "name": f"ReadAloud-{VERSION}-linux-x86_64.AppImage.001",
        "label": "Part 1 Data Slice",
        "size_str": "1.8 GB",
    },
    {
        "name": f"ReadAloud-{VERSION}-linux-x86_64.AppImage.002",
        "label": "Part 2 Data Slice",
        "size_str": "535 MB",
    },
]


def get_appimage_dir() -> Path:
    """Return the directory containing the running AppImage or executable."""
    appimage_env = os.environ.get("APPIMAGE")
    if appimage_env and os.path.exists(appimage_env):
        return Path(appimage_env).resolve().parent
    return Path(sys.argv[0]).resolve().parent


def get_data_dir() -> Path:
    """Return ~/.local/share/readaloud, creating it if necessary."""
    data_dir = Path.home() / ".local" / "share" / "readaloud"
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir


def get_assembled_path() -> Path:
    """Return the destination path for the assembled full AppImage."""
    return get_data_dir() / f"ReadAloud-{VERSION}-x86_64-full.AppImage"


def is_valid_assembled(path: Path) -> bool:
    """Verify if the assembled AppImage exists, is executable, and has valid size (> 1 GB)."""
    return path.is_file() and os.access(path, os.X_OK) and path.stat().st_size > 1_000_000_000


def find_slice(slice_name: str, appimage_dir: Path, data_dir: Path) -> Path | None:
    """Check if a slice file exists in the AppImage directory or data/downloads directory."""
    candidates = [
        appimage_dir / slice_name,
        data_dir / "downloads" / slice_name,
        data_dir / slice_name,
    ]
    for candidate in candidates:
        if candidate.is_file() and candidate.stat().st_size > 1_000_000:
            return candidate
    return None


def show_prompt_dialog(missing_slices: list[dict]) -> bool:
    """Prompt the user whether to download missing components automatically.

    Falls back in order: Zenity -> KDialog -> Tkinter -> CLI.
    """
    missing_text = "\n".join(
        f"  • {s['name']} ({s['size_str']})" for s in missing_slices
    )
    prompt_message = (
        f"ReadAloud requires the complete offline neural voice runtime (~2.3 GB total across 2 parts) "
        f"to synthesize speech without an internet connection.\n\n"
        f"The following required component file(s) are missing from this folder:\n\n"
        f"{missing_text}\n\n"
        f"Would you like ReadAloud to automatically download the missing component(s) "
        f"directly from GitHub into this folder now?"
    )

    # 1. Try Zenity
    if shutil.which("zenity") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        try:
            res = subprocess.run(
                [
                    "zenity",
                    "--question",
                    "--title=ReadAloud - Additional Components Required",
                    f"--text={prompt_message}",
                    "--ok-label=Download Now",
                    "--cancel-label=Cancel",
                    "--width=560",
                ],
                check=False,
            )
            return res.returncode == 0
        except Exception:
            pass

    # 2. Try KDialog
    if shutil.which("kdialog") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        try:
            res = subprocess.run(
                [
                    "kdialog",
                    "--title",
                    "ReadAloud - Additional Components Required",
                    "--yesno",
                    prompt_message,
                ],
                check=False,
            )
            return res.returncode == 0
        except Exception:
            pass

    # 3. Try Tkinter
    if os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"):
        try:
            import tkinter as tk
            from tkinter import messagebox
            root = tk.Tk()
            root.withdraw()
            ans = messagebox.askyesno(
                title="ReadAloud - Additional Components Required",
                message=prompt_message,
            )
            root.destroy()
            return bool(ans)
        except Exception:
            pass

    # 4. Fallback to CLI
    print("\n" + "=" * 70)
    print("ReadAloud - Additional Components Required")
    print("=" * 70)
    print(prompt_message)
    print("=" * 70)
    try:
        reply = input("\nDownload missing components now? [Y/n]: ").strip().lower()
        return reply in ("", "y", "yes")
    except (EOFError, KeyboardInterrupt):
        return False


def show_info_dialog(title: str, message: str):
    """Show an informational notification to the user."""
    if shutil.which("zenity") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        subprocess.run(["zenity", "--info", f"--title={title}", f"--text={message}", "--width=500"], check=False)
    elif shutil.which("kdialog") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        subprocess.run(["kdialog", "--title", title, "--msgbox", message], check=False)
    else:
        print(f"\n[{title}]\n{message}\n")


def show_error_dialog(title: str, message: str):
    """Show an error notification to the user."""
    if shutil.which("zenity") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        subprocess.run(["zenity", "--error", f"--title={title}", f"--text={message}", "--width=500"], check=False)
    elif shutil.which("kdialog") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")):
        subprocess.run(["kdialog", "--title", title, "--error", message], check=False)
    else:
        print(f"\n[ERROR: {title}]\n{message}\n", file=sys.stderr)


def download_file_with_progress(url: str, dest_path: Path, label: str) -> bool:
    """Download a file with visual progress reporting (Zenity or CLI)."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".tmp")

    headers = {"User-Agent": f"ReadAloud-Launcher/{VERSION} (Linux x86_64; automated-downloader)"}
    req = urllib.request.Request(url, headers=headers)

    use_zenity = bool(shutil.which("zenity") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")))
    zenity_proc = None

    if use_zenity:
        try:
            zenity_proc = subprocess.Popen(
                [
                    "zenity",
                    "--progress",
                    f"--title=ReadAloud Downloader - {label}",
                    f"--text=Connecting to GitHub Release v{VERSION}...\n({dest_path.name})",
                    "--percentage=0",
                    "--auto-close",
                    "--width=500",
                ],
                stdin=subprocess.PIPE,
                text=True,
            )
        except Exception:
            zenity_proc = None

    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0
            block_size = 1024 * 1024  # 1 MB blocks

            with open(temp_path, "wb") as f_out:
                while True:
                    chunk = response.read(block_size)
                    if not chunk:
                        break
                    f_out.write(chunk)
                    downloaded += len(chunk)

                    if total_size > 0:
                        pct = int((downloaded / total_size) * 100)
                        mb_done = downloaded / (1024 * 1024)
                        mb_total = total_size / (1024 * 1024)
                        status_str = f"Downloading {label}...\n{mb_done:.1f} MB of {mb_total:.1f} MB ({pct}%)"

                        if zenity_proc and zenity_proc.stdin:
                            try:
                                zenity_proc.stdin.write(f"{pct}\n")
                                zenity_proc.stdin.write(f"# {status_str}\n")
                                zenity_proc.stdin.flush()
                            except (BrokenPipeError, OSError):
                                pass
                        else:
                            print(f"\r[{label}] {mb_done:.1f}/{mb_total:.1f} MB ({pct}%)", end="", flush=True)

        if zenity_proc and zenity_proc.stdin:
            zenity_proc.stdin.close()
            zenity_proc.wait()

        if not use_zenity:
            print()

        # Atomic rename upon completion
        temp_path.replace(dest_path)
        return True

    except Exception as e:
        if zenity_proc:
            try:
                zenity_proc.kill()
            except Exception:
                pass
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        show_error_dialog(
            "Download Failed",
            f"Failed to download {dest_path.name}:\n{e}\n\n"
            f"Please check your internet connection or manually download from:\n{url}",
        )
        return False


def assemble_slices(slice1: Path, slice2: Path, dest_path: Path) -> bool:
    """Concatenate slice 1 and slice 2 into the target AppImage."""
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    temp_path = dest_path.with_suffix(".assembling")

    use_zenity = bool(shutil.which("zenity") and (os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY")))
    zenity_proc = None

    if use_zenity:
        try:
            zenity_proc = subprocess.Popen(
                [
                    "zenity",
                    "--progress",
                    "--title=ReadAloud - Assembling Runtime",
                    "--text=Combining multi-part data slices for first-time launch...",
                    "--pulsate",
                    "--auto-close",
                    "--width=500",
                ],
                stdin=subprocess.PIPE,
                text=True,
            )
        except Exception:
            zenity_proc = None

    try:
        block_size = 16 * 1024 * 1024  # 16 MB chunks

        with open(temp_path, "wb") as f_out:
            for s_path in (slice1, slice2):
                with open(s_path, "rb") as f_in:
                    while True:
                        buf = f_in.read(block_size)
                        if not buf:
                            break
                        f_out.write(buf)

        if zenity_proc:
            try:
                zenity_proc.stdin.close()
                zenity_proc.wait()
            except Exception:
                pass

        # Make executable
        os.chmod(temp_path, 0o755)
        temp_path.replace(dest_path)
        return True

    except Exception as e:
        if zenity_proc:
            try:
                zenity_proc.kill()
            except Exception:
                pass
        if temp_path.exists():
            try:
                temp_path.unlink()
            except Exception:
                pass
        show_error_dialog("Assembly Failed", f"Failed to assemble AppImage: {e}")
        return False


def create_desktop_entry(assembled_path: Path):
    """Register desktop entry in ~/.local/share/applications for system menu integration."""
    try:
        apps_dir = Path.home() / ".local" / "share" / "applications"
        apps_dir.mkdir(parents=True, exist_ok=True)
        desktop_file = apps_dir / "im.zackarious.ReadAloud.desktop"

        content = f"""[Desktop Entry]
Name=ReadAloud
GenericName=Text-to-Speech Reader
Comment=An elegant, private, offline Text-to-Speech reader
Exec="{assembled_path}" %U
Icon=im.zackarious.ReadAloud
Terminal=false
Type=Application
Categories=Utility;AudioVideo;Audio;Accessibility;
MimeType=text/plain;text/markdown;application/pdf;application/epub+zip;
StartupNotify=true
"""
        desktop_file.write_text(content, encoding="utf-8")
    except Exception:
        pass


def main():
    appimage_dir = get_appimage_dir()
    data_dir = get_data_dir()
    assembled_path = get_assembled_path()

    # 1. Check if assembled AppImage already exists
    if is_valid_assembled(assembled_path):
        os.execv(str(assembled_path), [str(assembled_path)] + sys.argv[1:])

    # Check if an assembled full AppImage is placed next to this launcher
    adjacent_assembled = appimage_dir / f"ReadAloud-{VERSION}-x86_64-full.AppImage"
    if is_valid_assembled(adjacent_assembled):
        os.execv(str(adjacent_assembled), [str(adjacent_assembled)] + sys.argv[1:])

    # 2. Check for slices
    found_slices = {}
    missing_slices = []

    for s in SLICES:
        p = find_slice(s["name"], appimage_dir, data_dir)
        if p:
            found_slices[s["name"]] = p
        else:
            missing_slices.append(s)

    # 3. If slices are missing, prompt user to download them
    if missing_slices:
        confirmed = show_prompt_dialog(missing_slices)
        if not confirmed:
            show_info_dialog(
                "ReadAloud Setup Notice",
                f"ReadAloud cannot proceed without all required component files.\n\n"
                f"You can manually download the missing files from:\n"
                f"{REPO_URL}/releases/tag/{RELEASE_TAG}\n\n"
                f"Place them in the same folder as this AppImage before running it again.",
            )
            sys.exit(0)

        # Determine download directory: prefer appimage_dir if writable, otherwise data_dir/downloads
        dl_dir = appimage_dir
        try:
            test_file = dl_dir / ".write_test"
            test_file.touch()
            test_file.unlink()
        except (PermissionError, OSError):
            dl_dir = data_dir / "downloads"
            dl_dir.mkdir(parents=True, exist_ok=True)

        for s in missing_slices:
            dest = dl_dir / s["name"]
            url = f"{DOWNLOAD_BASE_URL}/{s['name']}"
            success = download_file_with_progress(url, dest, s["label"])
            if not success:
                sys.exit(1)
            found_slices[s["name"]] = dest

    # 4. Assemble slices into the target full AppImage
    slice1_path = found_slices[SLICES[0]["name"]]
    slice2_path = found_slices[SLICES[1]["name"]]

    success = assemble_slices(slice1_path, slice2_path, assembled_path)
    if not success:
        sys.exit(1)

    # 5. Create desktop shortcut
    create_desktop_entry(assembled_path)

    # 6. Launch the assembled application
    os.execv(str(assembled_path), [str(assembled_path)] + sys.argv[1:])


if __name__ == "__main__":
    main()

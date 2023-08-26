#!/usr/bin/env python3

import argparse
import pathlib
import shutil
import subprocess
import tempfile
import textwrap
import urllib.request


def _sp(args):
    args = list(map(str, args))
    print(" ".join(args))
    subprocess.run(args, check=True)


def _(s):
    return textwrap.dedent(s).lstrip()

def build_builder_container():
    _sp(["podman", "build",
        "--cap-add", "sys_chroot",
        "-f", "Containerfile.aurbuilder",
        "-t", "aurbuilder:latest"])


def build_aur(name: str, dest: pathlib.Path) -> pathlib.Path:
    url = f"https://aur.archlinux.org/cgit/aur.git/snapshot/{name}.tar.gz"
    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)
        tarball_path = temp_dir / "tarball"
        with open(tarball_path, "wb") as tarball:
            shutil.copyfileobj(urllib.request.urlopen(url), tarball)

        try:
            # Note that -v:...:...:U chmods everything inside that path to
            # belong to the builder user, which needs to be reverted.
            # This is reverted in the finally statement.
            _sp(["podman", "run",
                 "--security-opt", "label=disable",
                 "--rm",
                 "-v", f"{temp_dir.absolute()}:/builder/tmp:U",
                 "-w", f"/builder/tmp",
                 "aurbuilder:latest",
                 "tar", "-xzvf", "tarball"])

            _sp(["podman", "run",
                 "--security-opt", "label=disable",
                 "--rm",
                 "-v", f"{(temp_dir / name).absolute()}:/builder/{name}",
                 "-w", f"/builder/{name}",
                 "aurbuilder:latest",
                 "makepkg",
                 "--syncdeps",
                 "--noconfirm"])

        finally:
            _sp(["podman", "run",
                 "--security-opt", "label=disable",
                 "--rm",
                 "-v", f"{temp_dir.absolute()}:/builder/tmp:U",
                 "-w", f"/builder/tmp",
                 "-u", "root",
                 "aurbuilder:latest",
                 "true"])

        generated_zsts = list((temp_dir / name).glob("*.zst"))
        assert len(generated_zsts) == 1
        generated_zst = generated_zsts[0]
        dest_zst = dest / generated_zst.name
        shutil.copyfile(generated_zst, dest_zst)
        return dest_zst


def build_container(packages, aur_packages, image):
    build_builder_container()

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_dir = pathlib.Path(temp_dir)

        packages = " ".join(packages)

        container_def = _(f"""
        FROM docker.io/library/archlinux:latest
        RUN pacman -Sy {packages} --noconfirm
        """)

        package_files = []
        for package in aur_packages or []:
            package_file = build_aur(package, temp_dir).name
            package_files.append(f"/pkgs/{package_file}")

        if package_files:
            package_files = " ".join(package_files)

            container_def += _(f"""
            RUN pacman -U {package_files} --noconfirm
            """)

        container_file_path = temp_dir / "Containerfile"
        with open(container_file_path, "w") as c:
            c.write(container_def)

        _sp(["podman", "build",
             "--cap-add", "sys_chroot",
             "-f", container_file_path.absolute(),
             "-t", image,
             "-v", f"{temp_dir.absolute()}:/pkgs",
             "--security-opt", "label=disable",])


def build_container_main():
    parser = argparse.ArgumentParser()
    parser.add_argument("image")
    parser.add_argument("--package", action="append")
    parser.add_argument("--aur-package", action="append")
    args = parser.parse_args()
    build_container(args.package, args.aur_package, args.image)


if __name__ == "__main__":
    build_container_main()

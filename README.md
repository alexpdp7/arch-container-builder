# `arch-container-builder`

```
$ ./builder.py --package kubectl --aur-package jsonnet-bundler-bin test
```

This builds the AUR package `jsonnet-bundler-bin`, and creates a container image with that package and `kubectl`.

## Motivation

I am looking to adopt [Toolbx](https://containertoolbx.org/)/[distrobox](https://github.com/89luca89/distrobox) to ensure my environments are reproducible.
These tools help you use software installed in a container image.

When researching how to build these images, I noticed that Nix and Arch Linux are the distros that have most of the software I want to use.
Nix's approach is really attractive, but it seems that using Nix images with Toolbx/distrobox might be more complex.
Additionally, adding non-packaged software to Nix looks complex, and using container images already gives me some of the advantages of Nix.

Arch Linux is a more traditional user distro, so it seems easier to adopt than Nix for this purpose.
While researching Arch Linux, I noticed that many packages in the AUR are "looser" than packages for other distros.
Some AUR packages fetch binaries from GitHub and most are not hermetic.
This "looseness" might explain why Arch Linux has so many packages.

However, AUR packages are more involved to install.
I searched for a tool that would take a list of mainline and AUR packages and build a container image, and I found none.
I decided to build a small tool for this purpose.

## Implementation

`arch-container-builder` is a `builder.py` Python script, and a `Containerfile.aurbuilder` container definition.
The builder first builds the `aurbuilder` image.
Then, for each AUR package, the builder builds the package using the `aurbuilder` image.
Then, the builder installs all the AUR package binaries and the mainline packages to an image.

Currently, this just works using rootless Podman.
(I have only tested this on a CentOS 9 Stream host.)

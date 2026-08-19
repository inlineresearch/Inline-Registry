# Inline Studio Registry

The list of published extensions & models

## Publishing an extension

1. Tag a release in your extension repo (e.g. `v1.0.0`). Installs pin to the commit behind the tag.
2. Add `registry/<your-id>.json` here, one file per extension so PRs never conflict:

```json
{
  "id": "your-id",
  "name": "Your Extension",
  "description": "One line on what it does.",
  "repo": "https://github.com/you/your-extension",
  "author": "You",
  "tags": ["image"]
}
```

**No version goes here.** A listing names your repository; Inline Studio resolves the newest
release tag at install and when checking for updates. Publish a new version by tagging it - you
never open another PR here.

3. Open a PR. `id` must match both the filename and your manifest's `id`.

## What CI checks

Your repo is cloned at the tag and put through **the same checks the app runs at install time**:

- the manifest validates, and its `id` matches this entry;
- the security scan finds nothing CRITICAL: declaring `torch`/`diffusers`/`numpy` as a dependency,
  `exec` over an encoded payload, a `setup.py`, or bundled CUDA/torch binaries all fail the build;
- HIGH/MEDIUM findings (subprocess, sockets, unrecognized network hosts) are reported as warnings.
  They don't block publication, but users must approve them at install.

`index.json` is generated from the validated entries; don't edit it.

## What this is not

Listing here is not an endorsement or a safety guarantee. Extensions run in the same process as
Inline Studio and can do anything it can. Review the code you install.

# Model registry

The list of models Inline Studio shows under **Settings → Models**.

One file, `models.json`, and everything in it is verified. An unverified model needs a channel of
its own so the default list stays trustworthy; add `models.dev.json` back when there is one to put
in it, and point `INLINE_MODEL_REGISTRY` at it to see them.

## Adding a model

Add an entry in models.json:

```json
{
  "id": "flux-2-klein-4b",
  "label": "FLUX.2 Klein 4B",
  "filename": "flux-2-klein-4b.safetensors",
  "category": "diffusion_models",
  "group": "flux-2-klein-4b",
  "precision": "",
  "source": {
    "kind": "hf_file",
    "repo": "Comfy-Org/flux2-klein-4B",
    "path": "split_files/diffusion_models/flux-2-klein-4b.safetensors"
  },
  "verified": true,
  "size_bytes": null,
  "updated": "2026-08-17"
}
```

Run `python scripts/validate_models.py` before opening a PR.

## What the app does with this

It resolves filenames. When a graph, a node or a training run names a file that is
not on disk, the app looks the name up here and offers the download.

**It never uses this to decide what a checkpoint is.** A model is identified from its own tensor
shapes, because `diffusion_models/` is shared across architectures and two encoders can have
identical shapes. A file listed under the wrong `category`, or a `filename` that does not match
what the repo actually serves, will download and then fail at generation. Get those right.

In case you want a model listed here, open a PR. 

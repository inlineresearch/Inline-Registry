# Inline Studio Extension Registry

The list of published extensions that Inline Studio shows under **Extensions → Available**.

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

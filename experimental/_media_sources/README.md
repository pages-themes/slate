# Media sources

This directory contains original, full-resolution media. Jekyll excludes it
from the published site.

- `images/people/`, `images/home/`, `images/lab/`, and `images/branding/`
  contain sources used by `make optimize-media`.
- `videos/` contains original video sources used by that command.
- `archive/` contains unused historical originals. Files in this directory do
  not produce published assets.

Run `make optimize-media` after changing an active source. Generated,
website-ready files are written to `assets/images/` and should be committed.
The command builds and validates all outputs in a temporary excluded directory
before atomically publishing them, so it is safe to run while `make serve` is
watching the repository.

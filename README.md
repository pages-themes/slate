# AutoDIAL Website

This repository contains the Jekyll website for the Autonomous Discovery of
Alloys (AutoDIAL) research group.

## Project documentation

- [Developer guide](docs/DEVELOPER_GUIDE.md): repository structure and
  task-oriented update procedures.
- [Verification plan](docs/TESTING.md): automated checks, browser review, and
  regression-test design.
- [Improvement roadmap](docs/ROADMAP.md): prioritized implementation work and
  acceptance criteria.
- [Agent feature map](docs/feature-map.yml): structured feature ownership,
  dependencies, update recipes, and validation contracts.

## Requirements

- Ruby and Bundler
- ImageMagick (`convert` and `identify`)
- FFmpeg (`ffmpeg` and `ffprobe`)
- Python 3.9 or newer for publication updates and private previews
- `zip` for creating a private review bundle
- Firefox and Geckodriver for `make test` and `make test-ui`

On Debian or Ubuntu, install the Ruby and media dependencies with:

```sh
make install
```

Install Firefox and Geckodriver separately when you need the real-browser
suite. They are preinstalled on the pinned GitHub Actions runner.

## Local development

Build the site once:

```sh
make build
```

Serve it locally with automatic rebuilding:

```sh
make serve
```

Jekyll will print the local address, normally
<http://127.0.0.1:4000>. Stop the server with `Ctrl-C`.

### Private review bundle

To share a draft without publishing the branch, create a ZIP from the current
checkout in a shell with the build dependencies installed:

```sh
./script/create-preview-bundle
```

The script runs `make check`, then writes a timestamped ZIP to `/tmp` and
prints its SHA-256 checksum. To choose the output file, pass an absolute path
in an existing directory; the file must not already exist:

```sh
./script/create-preview-bundle /tmp/autodial-colleague-review.zip
```

The ZIP contains the built site, a README, and `serve-preview.py`. Recipients
can extract it and run `python3 serve-preview.py` on macOS/Linux or
`py serve-preview.py` on Windows, then open <http://127.0.0.1:8000/>. The
viewer needs Python 3.9 or newer and serves only on the recipient's computer.
The bundle leaves out `CNAME` and internal review data. Share it privately;
the publication selection and News copy still await scientific and PI review.

### Experimental subdirectory build

To prepare the draft for a possible **later** public URL at
`https://autodiallab.ca/experimental/`, run:

```sh
./script/create-experimental-bundle
# Or choose a ZIP path:
./script/create-experimental-bundle /tmp/autodial-experimental-review.zip
```

Jekyll omits directories beginning with `_`, so `/experimental/` is a safer
path than `/_/experimental/` for this repository.

This creates a ZIP containing an `experimental/` folder built with Jekyll's
`baseurl`. It checks that local links and media stay under that path, removes
the nested `CNAME`, and leaves the root site untouched. If GitHub Pages
currently publishes from the root of `master`, the folder could be added there
**after** scientific and PI review and explicit publication approval. Verify
the actual Pages publishing source before doing so. The normal homepage would
keep its current source; no link to the draft is added there. The draft URL
would still be public and discoverable. Its pages request `noindex`, which is
not access control.

Most page content is stored in the Markdown files in the repository root.
Laboratory content is in `sdls.md`, and homepage content is in `index.md`.
Group-member records are maintained in `_data/members.yml`; reusable templates
under `_includes/` generate their cards and biography dialogs.

The Publications page reads reviewed records from `_data/publications.json`.
Run `make publications-update` to discover candidates, review them with
`make publications-review`, then run `make publications-build` after recording
individual approval decisions. Discovery alone never adds a paper to the site.
See [the Publications workflow](docs/PUBLICATIONS_WORKFLOW.md) for the full
review process and source-verification rules.

Publication News posts live in `_news/publications/`. Each post records a DOI,
publication month, source links, and a provisional summary. The News page draws
the full citation from the reviewed bibliography, keeping bibliographic details
in one place. See `how_to_write_news_post.txt` for the post format.

The Software page reads `_data/software.yml`; add or revise packages there
instead of editing card markup. AutoEIS documentation remains available at
`https://autodiallab.ca/AutoEIS/` through its Software card.

## Updating media

Original, full-resolution media belongs under `_media_sources/`. Files used by
the current website are organized under:

```text
_media_sources/
├── images/
│   ├── branding/
│   ├── home/
│   ├── lab/
│   └── people/
├── videos/
└── archive/        # Historical media not currently published
```

After adding or replacing an active source file, generate the website-ready
versions with:

```sh
make optimize-media
```

The generated files are written to `assets/images/`. Commit both the source and
generated files. The optimizer validates all outputs and publishes them
atomically, so it is safe to run while `make serve` is active.

Portrait filenames must have unique stems. For example,
`_media_sources/images/people/Jane_Doe.jpg` produces:

```text
assets/images/people/Jane_Doe-300.webp
assets/images/people/Jane_Doe-600.webp
```

### Adding or updating a group member

Each person is represented once in `_data/members.yml`. Section and member
order in that file controls the rendered order. A member record contains a
stable lowercase `id`, their displayed `name`, modal `role`, portrait filename
stem in `photo`, HTML biography in `bio`, and optional profile `links` and
`card_title`.

To add a member:

1. Add the original portrait to `_media_sources/images/people/`.
2. Add the member record to the appropriate section in `_data/members.yml`.
3. Run `make optimize-media` to generate the 300px and 600px portraits.
4. Run `make check` and inspect the page with `make serve`.

To move someone to alumni, move their complete record to the `alumni` section
and update `role` or `card_title` as needed. The portrait and biography do not
need to be duplicated.

## Validation

Run the complete local check before committing:

```sh
make check
```

This command performs a clean Jekyll build, checks internal HTML links, and
validates the media referenced by the generated pages. It detects missing or
empty files, corrupted images, incorrectly sized portraits, non-H.264 videos,
differences between `assets/` and `_site/`, and accidental publication of
`_media_sources/`. It also validates member records, unique identifiers,
profile URLs, source portraits, rendered ordering, and the one-to-one mapping
between member cards and biography dialogs. It also runs generated-HTML
contract tests for page metadata, landmarks, navigation, accessible control
names, images, duplicate IDs, dialog relationships, and video markup.

For structural, layout, CSS, or JavaScript changes, run the real-browser suite:

```sh
make test
```

This includes `make check` and then uses headless Firefox to exercise primary
routes, skip navigation, member dialogs with mouse and keyboard, focus trapping,
phone-width layout, news navigation, and CorrosionMAP playback and seeking.

GitHub Actions runs the same checks for pushes and pull requests, followed by
the theme's Ruby, HTML, and package checks.

## Typical update workflow

1. Edit the appropriate Markdown file.
2. Put new original media in `_media_sources/`, if needed.
3. Run `make optimize-media` after changing media.
4. Run `make check`.
5. Run `make test` for layout, template, or interaction changes.
6. Run `make serve` and inspect the affected pages in a browser.
7. Commit the content, original media, and generated media together.

Run `make help` to see the available Makefile commands.

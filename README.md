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

On the local redesign branch, `make serve` shows the original root site at
<http://127.0.0.1:4000/> and the isolated draft source in
[`experimental/`](experimental/README.md) at
<http://127.0.0.1:4000/experimental/>. Editing files under `experimental/`
rebuilds the draft. `make check` and `make test` validate both sites. The
original site source stays at the repository root; `CNAME` remains there only.
If port 4000 is occupied, use `make serve LOCAL_PORT=4002`.

Publication discovery, review decisions, News posts, Software entries, and
their maintenance scripts live under `experimental/`. Use the commands in
[`experimental/README.md`](experimental/README.md) to update and preview them.
Nothing in this branch is published by running the local build commands.
See [the Pages publication plan](docs/PAGES_PUBLICATION.md) for the prepared
manual workflow and the approval steps required before public deployment.

Most page content is stored in the Markdown files in the repository root.
Laboratory content is in `sdls.md`, and homepage content is in `index.md`.
Group-member records are maintained in `_data/members.yml`; reusable templates
under `_includes/` generate their cards and biography dialogs.

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

APT_GET ?= sudo apt-get
BUNDLE ?= bundle
GEM ?= gem
RUBY_PACKAGES ?= ruby-full build-essential zlib1g-dev bundler
MEDIA_PACKAGES ?= imagemagick ffmpeg
PYTHON ?= python3
PUBLICATIONS_DISCOVER_FLAGS ?= --no-crossref
PUBLICATIONS_LIST_LIMIT ?= 25

.PHONY: install install-system install-gems optimize-media build check test test-ui serve clean publications-update publications-review publications-build

# Show documentation and some recommended commands and instructions for using this Makefile.
help:
	@echo "Makefile for building and serving the Jekyll site."
	@echo ""
	@echo "Usage:"
	@echo "  make install          Install system dependencies and Ruby gems."
	@echo "  make optimize-media   Generate web-ready images and video."
	@echo "  make build            Build the Jekyll site."
	@echo "  make check            Build and validate the site and its media."
	@echo "  make test             Run the full local check and browser interaction tests."
	@echo "  make test-ui          Build and run browser interaction tests."
	@echo "  make serve            Serve the Jekyll site locally."
	@echo "  make publications-update  Discover OpenAlex and arXiv candidates; do not change the site."
	@echo "  make publications-review  Show candidate counts and the newest pending records."
	@echo "  make publications-build   Regenerate the site bibliography from approved records only."
	@echo ""
	@echo "Environment Variables:"
	@echo "  APT_GET               Command to use for package installation (default: sudo apt-get)."
	@echo "  BUNDLE                Command to use for Bundler (default: bundle)."
	@echo "  GEM                   Command to use for RubyGems (default: gem)."
	@echo "  RUBY_PACKAGES         List of Ruby packages to install (default: ruby-full build-essential zlib1g-dev bundler)."
	@echo "  MEDIA_PACKAGES        Media tools to install (default: imagemagick ffmpeg)."
	@echo "  PUBLICATIONS_DISCOVER_FLAGS  OpenAlex discovery flags (default: --no-crossref)."
	@echo "  PUBLICATIONS_LIST_LIMIT     Pending records shown by publications-review (default: 25)."

install: install-system install-gems

install-system:
	@if command -v apt-get >/dev/null 2>&1; then \
		$(APT_GET) update; \
		$(APT_GET) install -y $(RUBY_PACKAGES) $(MEDIA_PACKAGES); \
	else \
		echo "apt-get not found; install Ruby, Bundler, and build tools manually."; \
	fi

install-gems:
	@if ! command -v $(BUNDLE) >/dev/null 2>&1; then \
		$(GEM) install --user-install bundler; \
	fi
	$(BUNDLE) config set path vendor/bundle
	$(BUNDLE) install

optimize-media:
	./script/optimize-media

build:
	$(BUNDLE) exec jekyll clean
	$(BUNDLE) exec jekyll build

check:
	./script/check-site

test: check
	./script/test-ui

test-ui: build
	./script/test-ui

serve:
	$(BUNDLE) exec jekyll serve

# Discovery only changes internal candidate/review files. Publishing still
# requires an individual approval and a separate publications-build command.
publications-update:
	$(PYTHON) script/publications.py discover $(PUBLICATIONS_DISCOVER_FLAGS)
	$(PYTHON) script/publications.py discover-arxiv
	$(PYTHON) script/publications.py report
	@echo "Candidates refreshed; review them before running make publications-build."

publications-review:
	$(PYTHON) script/publications.py report
	$(PYTHON) script/publications.py list --status pending --limit $(PUBLICATIONS_LIST_LIMIT)

publications-build:
	$(PYTHON) script/publications.py build

clean:
	$(BUNDLE) exec jekyll clean

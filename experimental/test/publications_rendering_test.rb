# frozen_string_literal: true

require "fileutils"
require "jekyll"
require "json"
require "minitest/autorun"
require "nokogiri"
require "tmpdir"

class PublicationsRenderingTest < Minitest::Test
  ROOT = File.expand_path("..", __dir__)

  def test_approved_records_render_by_year_with_types_and_optional_resources
    records = [
      publication("older", year: 2022, type: "other", title: "Older example"),
      publication("recent", year: 2025, type: "journal", title: "Recent example").merge(
        "doi" => "10.1234/recent",
        "doi_url" => "https://doi.org/10.1234/recent",
        "links" => [
          { "label" => "Software", "url" => "https://example.org/software" },
          { "label" => "Dataset", "url" => "https://example.org/dataset" }
        ],
        "image" => { "src" => "/assets/images/test-figure.png", "alt" => "Synthetic test figure",
                     "width" => 640, "height" => 360, "caption" => "Fixture only" }
      ),
      publication("preprint", year: 2025, type: "preprint", title: "Preprint example").merge(
        "doi" => "10.48550/arxiv.2607.19307",
        "doi_url" => "https://doi.org/10.48550/arxiv.2607.19307"
      )
    ]
    document = render(records)

    assert_equal %w[2025 2022], document.css(".publication-year h2").map { |heading| heading.text.strip }
    assert_equal 3, document.css(".publication-card").length
    assert_equal %w[journal other preprint], document.css(".publication-card").map { |card| card["data-publication-type"] }.sort
    recent = document.at_css("#publication-recent")
    assert_equal "10.1234/recent", recent.at_css(".publication-card__doi a").text
    assert_equal "https://doi.org/10.1234/recent", recent.at_css(".publication-card__doi a")["href"]
    assert_equal ["Software", "Dataset"], recent.css(".publication-card__links a").map { |link| link.text.strip.delete("↗").strip }
    assert_equal "Synthetic test figure", recent.at_css("img")["alt"]
    assert_equal "640", recent.at_css("img")["width"]
    assert_equal "Fixture only", recent.at_css("figcaption").text.strip
    preprint = document.at_css("#publication-preprint")
    assert_equal "Preprint", preprint.at_css(".publication-card__type").text.strip
    assert_equal "https://doi.org/10.48550/arxiv.2607.19307", preprint.at_css(".publication-card__doi a")["href"]
    assert_empty preprint.css(".publication-card__links")
    assert document.at_css("#publication-search")
    assert document.at_css("#publication-type")
    assert document.at_css("#publication-year")
    assert document.at_css('script[src="/assets/js/publications.js"]')
  end

  def test_empty_bibliography_shows_review_message_without_filters
    document = render([])
    assert_includes document.at_css(".publication-empty").text, "being prepared for review"
    assert_empty document.css(".publication-card")
    assert_nil document.at_css("#publication-search")
  end

  private

  def publication(id, year:, type:, title:)
    { "id" => "publication-#{id}", "title" => title, "authors" => ["A. Researcher"],
      "venue" => "Example venue", "year" => year, "type" => type, "doi" => nil,
      "doi_url" => nil, "links" => [], "image" => nil }
  end

  def render(records)
    Dir.mktmpdir("autodial-publications-") do |source|
      FileUtils.mkdir_p(File.join(source, "_includes"))
      FileUtils.mkdir_p(File.join(source, "_layouts"))
      FileUtils.mkdir_p(File.join(source, "_data"))
      FileUtils.cp(File.join(ROOT, "publications.md"), source)
      FileUtils.cp(File.join(ROOT, "_includes/publication-card.html"), File.join(source, "_includes"))
      File.write(File.join(source, "_layouts/default.html"), "<!doctype html><html lang=\"en\"><body>{{ content }}</body></html>")
      File.write(File.join(source, "_data/publications.json"), JSON.generate(records))
      destination = File.join(source, "_site")
      config = Jekyll.configuration("source" => source, "destination" => destination,
                                    "quiet" => true, "disable_disk_cache" => true)
      Jekyll::Site.new(config).process
      Nokogiri::HTML(File.read(File.join(destination, "publications.html")))
    end
  end
end

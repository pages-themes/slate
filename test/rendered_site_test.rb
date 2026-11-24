# frozen_string_literal: true

require "minitest/autorun"
require "nokogiri"
require "set"

class RenderedSiteTest < Minitest::Test
  SITE_ROOT = File.expand_path("../_site", __dir__)
  PRIMARY_PAGES = {
    "index.html" => {
      title: "Home",
      description: "AutoDIAL develops autonomous materials-discovery platforms, high-throughput experiments, and " \
                   "trustworthy AI at the University of Toronto."
    },
    "news.html" => {
      title: "News & Updates",
      description: "News, research updates, publications, and group activities from AutoDIAL."
    },
    "sdls.html" => {
      title: "Self Driving Labs",
      description: "Explore AutoDIAL self-driving laboratory platforms for corrosion mapping, electrochemistry, " \
                   "and battery research."
    },
    "group_members.html" => {
      title: "Group Members and Alumni",
      description: "Meet the researchers, students, automation specialists, and alumni of the AutoDIAL research group."
    },
    "openings.html" => {
      title: "Openings",
      description: "Current research and employment opportunities with the AutoDIAL group."
    },
    "contact.html" => {
      title: "Contact",
      description: "Contact the AutoDIAL research group at the University of Toronto."
    }
  }.freeze
  EXPECTED_NAVIGATION = {
    "Home" => "/",
    "News" => "/news",
    "Self Driving Labs" => "/sdls",
    "Group Members" => "/group_members",
    "Openings" => "/openings",
    "Contact" => "/contact"
  }.freeze
  INLINE_EVENT_ATTRIBUTES = %w[
    onclick ondblclick onkeydown onkeypress onkeyup onmousedown onmouseenter
    onmouseleave onmousemove onmouseout onmouseover onmouseup
  ].freeze

  def setup
    missing_pages = PRIMARY_PAGES.keys.reject { |path| File.file?(File.join(SITE_ROOT, path)) }
    assert_empty missing_pages, "Run `make build` first; missing generated pages: #{missing_pages.join(', ')}"
  end

  def test_primary_pages_have_unique_specific_metadata
    titles = Set.new
    descriptions = Set.new

    each_primary_page do |path, document, expected|
      title = document.at_css("title")&.text&.strip
      description = document.at_css('meta[name="description"]')&.[]("content")&.strip

      assert_includes title, expected.fetch(:title), "#{path} has the wrong document title"
      assert_equal expected.fetch(:description), description, "#{path} has the wrong description"
      assert titles.add?(title), "Duplicate primary-page title: #{title.inspect}"
      assert descriptions.add?(description), "Duplicate primary-page description: #{description.inspect}"
    end
  end

  def test_primary_pages_expose_understandable_landmarks_and_headings
    each_primary_page do |path, document, _expected|
      assert_equal "en-US", document.at_css("html")&.[]("lang"), "#{path} must declare its language"
      assert_equal 1, document.css("main#main_content").length, "#{path} must have one main landmark"
      assert_equal 1, document.css("nav#sidebar").length, "#{path} must have one primary navigation landmark"
      refute_empty document.css("main#main_content h1"), "#{path} must have a visible content heading"

      skip_link = document.at_css('a.skip-link[href="#main_content"]')
      refute_nil skip_link, "#{path} must provide a skip link"
      assert_equal "Skip to main content", skip_link.text.strip
    end
  end

  def test_primary_navigation_is_complete_and_stable
    each_primary_page do |path, document, _expected|
      actual = document.css("nav#sidebar a").to_h { |link| [link.text.strip, link["href"]] }

      EXPECTED_NAVIGATION.each do |label, href|
        assert_equal href, actual[label], "#{path} has an incorrect #{label.inspect} navigation target"
      end
    end
  end

  def test_interactive_controls_have_accessible_names_and_safe_new_tabs
    each_primary_page do |path, document, _expected|
      document.css("a, button").each do |control|
        accessible_name = control["aria-label"].to_s.strip
        accessible_name = control.text.strip if accessible_name.empty?
        if accessible_name.empty?
          accessible_name = control.at_css("img")&.[]("alt").to_s.strip
        end

        refute_empty accessible_name, "#{path} has an unnamed #{control.name}: #{control}"

        next unless control.name == "a" && control["target"] == "_blank"

        rel_values = control["rel"].to_s.split
        assert_includes rel_values, "noopener", "#{path} has an unsafe target=_blank link"
        assert_includes rel_values, "noreferrer", "#{path} has an unsafe target=_blank link"
      end
    end
  end

  def test_images_reserve_space_and_have_alternative_text
    each_primary_page do |path, document, _expected|
      document.css("img").each do |image|
        refute_empty image["alt"].to_s.strip, "#{path} has an image without alternative text: #{image['src']}"
        assert_match(/\A\d+\z/, image["width"].to_s, "#{path} image is missing numeric width: #{image['src']}")
        assert_match(/\A\d+\z/, image["height"].to_s, "#{path} image is missing numeric height: #{image['src']}")
      end
    end
  end

  def test_primary_pages_have_no_duplicate_ids_or_inline_event_handlers
    each_primary_page do |path, document, _expected|
      duplicate_ids = document.xpath("//*[@id]").map { |node| node["id"] }.tally.select { |_id, count| count > 1 }
      assert_empty duplicate_ids, "#{path} has duplicate IDs: #{duplicate_ids.keys.join(', ')}"

      selector = INLINE_EVENT_ATTRIBUTES.map { |attribute| "//*[@#{attribute}]" }.join(" | ")
      inline_handlers = document.xpath(selector)
      assert_empty inline_handlers, "#{path} uses inline event handlers; bind behavior from a script instead"
    end
  end

  def test_member_dialogs_have_complete_accessibility_relationships
    document = parse("group_members.html")

    document.css(".person-trigger").each do |trigger|
      dialog_id = trigger["aria-controls"]
      dialog = document.at_css("##{dialog_id}")

      assert_equal "dialog", trigger["aria-haspopup"]
      refute_nil dialog, "Missing dialog controlled by #{trigger['data-member-id']}"
      assert_equal "dialog", dialog["role"]
      assert_equal "true", dialog["aria-modal"]
      assert dialog.key?("hidden"), "#{dialog_id} must be hidden before interaction"
      refute_nil document.at_css("##{dialog['aria-labelledby']}"), "#{dialog_id} has a broken aria-labelledby"
      refute_nil document.at_css("##{dialog['aria-describedby']}"), "#{dialog_id} has a broken aria-describedby"
    end
  end

  def test_corrosion_map_video_has_a_clear_browser_contract
    document = parse("sdls.html")
    video = document.at_css("video")

    refute_nil video, "Self Driving Labs page must contain the CorrosionMAP video"
    assert video.key?("controls"), "CorrosionMAP video must expose browser controls"
    assert video.key?("playsinline"), "CorrosionMAP video must play inline on mobile"
    assert_equal "metadata", video["preload"]
    assert_equal "/assets/images/lab/corrosion_map_1-poster.webp", video["poster"]

    source = video.at_css('source[type="video/mp4"]')
    refute_nil source, "CorrosionMAP video must declare an MP4 source"
    assert_equal "/assets/images/lab/corrosion_map_1.mp4", source["src"]
  end

  private

  def each_primary_page
    PRIMARY_PAGES.each do |path, expected|
      yield path, parse(path), expected
    end
  end

  def parse(path)
    Nokogiri::HTML(File.read(File.join(SITE_ROOT, path)))
  end
end

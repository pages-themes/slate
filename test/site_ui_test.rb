# frozen_string_literal: true

require "base64"
require "fileutils"
require "minitest/autorun"
require_relative "support/webdriver_client"

class SiteUiTest < Minitest::Test
  SITE_URL = ENV.fetch("SITE_URL", "http://127.0.0.1:4001")
  WEBDRIVER_URL = ENV.fetch("WEBDRIVER_URL", "http://127.0.0.1:4445")
  PRIMARY_ROUTES = {
    "/" => "Home",
    "/news" => "News & Updates",
    "/sdls" => "Self Driving Labs",
    "/group_members" => "Group Members and Alumni",
    "/openings" => "Openings",
    "/contact" => "Contact"
  }.freeze

  def self.browser
    @browser ||= WebDriverClient.new(WEBDRIVER_URL).start
  end

  def self.close_browser
    @browser&.close
  end

  def setup
    browser.set_window(width: 1280, height: 900)
  end

  def teardown
    capture_failure_screenshot unless passed?
  end

  def test_primary_routes_render_without_broken_core_ui
    PRIMARY_ROUTES.each do |route, expected_title|
      navigate(route)
      state = browser.execute(<<~JS)
        const main = document.querySelector("main#main_content");
        const eagerBrokenImages = Array.from(document.images).filter((image) =>
          image.loading !== "lazy" && (!image.complete || image.naturalWidth === 0)
        ).map((image) => image.currentSrc || image.src);
        return {
          readyState: document.readyState,
          title: document.title,
          main: Boolean(main),
          heading: main?.querySelector("h1")?.textContent.trim() || "",
          navigationLabels: Array.from(document.querySelectorAll("#sidebar a"))
            .map((link) => link.textContent.trim()),
          eagerBrokenImages,
          horizontalOverflow: document.documentElement.scrollWidth >
            document.documentElement.clientWidth + 1
        };
      JS

      assert_equal "complete", state.fetch("readyState"), "#{route} did not finish loading"
      assert_includes state.fetch("title"), expected_title, "#{route} has the wrong browser title"
      assert state.fetch("main"), "#{route} has no main landmark"
      refute_empty state.fetch("heading"), "#{route} has no understandable content heading"
      assert_includes state.fetch("navigationLabels"), "Group Members"
      assert_empty state.fetch("eagerBrokenImages"), "#{route} has broken eager images"
      refute state.fetch("horizontalOverflow"), "#{route} overflows the desktop viewport"
    end
  end

  def test_skip_link_is_first_keyboard_target_and_moves_to_main_content
    navigate("/")
    browser.execute("document.activeElement.blur(); document.body.focus();")
    browser.key(:tab)

    focused = browser.execute(<<~JS)
      const active = document.activeElement;
      const rect = active.getBoundingClientRect();
      return {
        className: active.className,
        text: active.textContent.trim(),
        visible: rect.bottom > 0 && rect.top < window.innerHeight
      };
    JS
    assert_includes focused.fetch("className"), "skip-link"
    assert_equal "Skip to main content", focused.fetch("text")
    assert focused.fetch("visible"), "Skip link must become visible when focused"

    browser.key(:enter)
    result = browser.wait_until do
      browser.execute(<<~JS)
        return location.hash === "#main_content" && document.activeElement.id === "main_content";
      JS
    end
    assert result, "Skip link did not move keyboard focus to the main content"
  end

  def test_member_dialog_supports_mouse_and_backdrop_interactions
    navigate("/group_members")
    browser.click('[data-member-id="yutong-liu"]')

    state = wait_for_dialog_image("yutong-liu")
    assert_equal false, state.fetch("hidden")
    assert_equal "Yutong Liu", state.fetch("name")
    assert_equal "Post Doc", state.fetch("role")
    assert_equal "modal-close", state.fetch("activeClass")
    assert_equal 600, state.fetch("imageWidth")
    assert state.fetch("bodyLocked"), "Opening a dialog must prevent background scrolling"

    browser.click("#member-dialog-yutong-liu .modal-name")
    refute dialog_hidden?("yutong-liu"), "Clicking dialog content must not close it"
    assert_equal "#{SITE_URL}/group_members", browser.current_url,
                 "Clicking dialog content must not follow an external profile link"

    browser.execute('document.getElementById("member-dialog-yutong-liu").click();')
    assert dialog_hidden?("yutong-liu"), "Clicking the backdrop must close the dialog"
    assert_equal "yutong-liu", focused_member_id

    browser.click('[data-member-id="yutong-liu"]')
    browser.click("#member-dialog-yutong-liu .modal-close")
    assert dialog_hidden?("yutong-liu"), "Close button must close the dialog"
    assert_equal "yutong-liu", focused_member_id
  end

  def test_member_dialog_keyboard_flow_traps_and_restores_focus
    navigate("/group_members")
    browser.execute('document.querySelector("[data-member-id=\\"changjun-cheng\\"]").focus();')
    browser.key(:enter)

    assert_equal "modal-close", active_element.fetch("className")
    refute dialog_hidden?("changjun-cheng")

    browser.modified_key(:shift, :tab)
    last_control = active_element
    assert_equal "A", last_control.fetch("tagName")
    assert_includes last_control.fetch("href"), "scholar.google.com"

    browser.key(:tab)
    assert_equal "modal-close", active_element.fetch("className"), "Tab must wrap to the first dialog control"

    browser.key(:escape)
    assert dialog_hidden?("changjun-cheng"), "Escape must close the dialog"
    assert_equal "changjun-cheng", focused_member_id, "Focus must return to the member selected by the user"
  end

  def test_member_page_remains_operable_at_mobile_width
    navigate("/")
    browser.execute(<<~JS)
      document.body.innerHTML = '<iframe id="mobile-frame" title="Mobile test viewport" ' +
        'style="border:0;height:812px;width:375px"></iframe>';
      document.getElementById("mobile-frame").src = "#{SITE_URL}/group_members";
    JS
    browser.wait_until do
      browser.execute(<<~JS)
        const frame = document.getElementById("mobile-frame");
        return frame.contentDocument?.readyState === "complete" &&
          Boolean(frame.contentDocument.querySelector(".member-grid"));
      JS
    end

    layout = browser.execute(<<~JS)
      const document = window.frames[0].document;
      const grid = document.querySelectorAll(".member-grid")[1];
      return {
        viewportWidth: document.documentElement.clientWidth,
        scrollWidth: document.documentElement.scrollWidth,
        columns: getComputedStyle(grid).gridTemplateColumns.split(" ").filter(Boolean).length
      };
    JS
    assert_operator layout.fetch("viewportWidth"), :>=, 350
    assert_operator layout.fetch("viewportWidth"), :<=, 375
    assert_operator layout.fetch("scrollWidth"), :<=, layout.fetch("viewportWidth") + 1
    assert_equal 1, layout.fetch("columns"), "Member grid must collapse to one column on a narrow phone"

    browser.execute('window.frames[0].document.querySelector("[data-member-id=\\"yutong-liu\\"]").click();')
    modal = browser.execute(<<~JS)
      const document = window.frames[0].document;
      const content = document.querySelector("#member-dialog-yutong-liu .modal-content");
      const close = content.querySelector(".modal-close");
      const rect = content.getBoundingClientRect();
      const closeRect = close.getBoundingClientRect();
      return {
        left: rect.left,
        right: rect.right,
        viewportWidth: document.documentElement.clientWidth,
        closeVisible: closeRect.bottom > 0 && closeRect.top < window.innerHeight
      };
    JS
    assert_operator modal.fetch("left"), :>=, -1
    assert_operator modal.fetch("right"), :<=, modal.fetch("viewportWidth") + 1
    assert modal.fetch("closeVisible"), "Dialog close button must remain visible on a phone"
    browser.execute(<<~JS)
      window.frames[0].document.dispatchEvent(
        new KeyboardEvent("keydown", {key: "Escape", bubbles: true})
      );
    JS
  end

  def test_news_navigation_and_video_playback
    navigate("/news")
    browser.click(".blog-title a")
    news = browser.execute(<<~JS)
      return {
        path: location.pathname,
        heading: document.querySelector("main h1")?.textContent.trim() || ""
      };
    JS
    assert_match(%r{\A/news/}, news.fetch("path"))
    assert_equal "Welcome to Our Research Group", news.fetch("heading")

    navigate("/sdls")
    metadata = browser.execute_async(<<~JS)
      const done = arguments[arguments.length - 1];
      const video = document.querySelector("video");
      const finish = () => done({
        readyState: video.readyState,
        networkState: video.networkState,
        duration: video.duration,
        videoWidth: video.videoWidth,
        canPlayH264: video.canPlayType('video/mp4; codecs="avc1.42E01E"')
      });
      if (video.readyState >= 1) {
        finish();
      } else {
        video.addEventListener("loadedmetadata", finish, {once: true});
        video.addEventListener("error", finish, {once: true});
        setTimeout(finish, 10000);
        video.load();
      }
    JS
    assert_operator metadata.fetch("readyState"), :>=, 1
    refute_equal 3, metadata.fetch("networkState"), "Browser reports that the video has no usable source"
    assert_operator metadata.fetch("duration"), :>, 0
    assert_operator metadata.fetch("videoWidth"), :>, 0
    refute_empty metadata.fetch("canPlayH264"), "Browser does not report H.264 MP4 support"

    playback = browser.execute_async(<<~JS)
      const done = arguments[arguments.length - 1];
      const video = document.querySelector("video");
      video.muted = true;
      video.play().then(() => {
        const target = Math.min(1, Math.max(0, video.duration / 2));
        const finish = () => {
          const result = {played: !video.paused, currentTime: video.currentTime};
          video.pause();
          done(result);
        };
        video.addEventListener("seeked", finish, {once: true});
        video.currentTime = target;
        setTimeout(finish, 10000);
      }).catch((error) => done({played: false, error: error.name}));
    JS
    assert playback.fetch("played"), "Video did not play: #{playback['error']}"
    assert_operator playback.fetch("currentTime"), :>, 0, "Video did not seek to a common playback position"
  end

  private

  def browser
    self.class.browser
  end

  def navigate(path)
    browser.navigate("#{SITE_URL}#{path}")
  end

  def dialog_hidden?(member_id)
    browser.execute("return document.getElementById('member-dialog-#{member_id}').hidden;")
  end

  def focused_member_id
    browser.execute("return document.activeElement.dataset.memberId || null;")
  end

  def active_element
    browser.execute(<<~JS)
      const active = document.activeElement;
      return {
        className: active.className,
        href: active.href || "",
        tagName: active.tagName
      };
    JS
  end

  def wait_for_dialog_image(member_id)
    browser.wait_until do
      browser.execute(<<~JS)
        const dialog = document.getElementById("member-dialog-#{member_id}");
        const image = dialog.querySelector(".modal-image");
        if (!image.complete || image.naturalWidth === 0) return null;
        return {
          hidden: dialog.hidden,
          name: dialog.querySelector(".modal-name").textContent.trim(),
          role: dialog.querySelector(".modal-title").textContent.trim(),
          activeClass: document.activeElement.className,
          imageWidth: image.naturalWidth,
          bodyLocked: document.body.classList.contains("member-dialog-open")
        };
      JS
    end
  end

  def capture_failure_screenshot
    artifact_dir = ENV["UI_TEST_ARTIFACT_DIR"]
    return if artifact_dir.to_s.empty?

    FileUtils.mkdir_p(artifact_dir)
    filename = name.gsub(/[^a-zA-Z0-9_-]+/, "-")
    path = File.join(artifact_dir, "#{filename}.png")
    File.binwrite(path, Base64.decode64(browser.screenshot))
    warn "Saved failed browser-test screenshot to #{path}"
  rescue StandardError => e
    warn "Could not save browser-test screenshot: #{e.message}"
  end
end

Minitest.after_run { SiteUiTest.close_browser }

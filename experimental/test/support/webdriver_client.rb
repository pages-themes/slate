# frozen_string_literal: true

require "json"
require "net/http"
require "uri"

class WebDriverClient
  COMMAND_READ_TIMEOUT = 30
  SESSION_START_READ_TIMEOUT = 90
  ELEMENT_KEY = "element-6066-11e4-a52e-4f735466cecf"
  KEY = {
    escape: "\uE00C",
    enter: "\uE007",
    shift: "\uE008",
    space: "\uE00D",
    tab: "\uE004"
  }.freeze

  def initialize(endpoint)
    @endpoint = URI(endpoint)
    @session_id = nil
  end

  def start
    session = request(:post, "/session", {
      capabilities: {
        alwaysMatch: {
          browserName: "firefox",
          acceptInsecureCerts: false,
          pageLoadStrategy: "normal",
          "moz:firefoxOptions": {
            args: ["-headless"],
            prefs: {
              "media.autoplay.default": 0,
              "media.autoplay.blocking_policy": 0
            }
          }
        }
      }
    }, read_timeout: SESSION_START_READ_TIMEOUT)
    @session_id = session.fetch("sessionId")
    self
  end

  def close
    request(:delete, session_path) if @session_id
  rescue StandardError => e
    warn "Could not close WebDriver session: #{e.message}"
  ensure
    @session_id = nil
  end

  def navigate(url)
    request(:post, session_path("url"), { url: url })
  end

  def current_url
    request(:get, session_path("url"))
  end

  def set_window(width:, height:)
    request(:post, session_path("window/rect"), { width: width, height: height })
  end

  def find(css_selector)
    element = request(:post, session_path("element"), {
      using: "css selector",
      value: css_selector
    })
    element.fetch(ELEMENT_KEY)
  end

  def click(css_selector)
    element_id = find(css_selector)
    request(:post, session_path("element/#{element_id}/click"))
  end

  def execute(script, *args)
    request(:post, session_path("execute/sync"), { script: script, args: args })
  end

  def execute_async(script, *args)
    request(:post, session_path("execute/async"), { script: script, args: args })
  end

  def key(key_name)
    value = KEY.fetch(key_name)
    request(:post, session_path("actions"), {
      actions: [{
        type: "key",
        id: "keyboard",
        actions: [
          { type: "keyDown", value: value },
          { type: "keyUp", value: value }
        ]
      }]
    })
  ensure
    release_actions
  end

  def modified_key(modifier, key_name)
    modifier_value = KEY.fetch(modifier)
    key_value = KEY.fetch(key_name)
    request(:post, session_path("actions"), {
      actions: [{
        type: "key",
        id: "keyboard",
        actions: [
          { type: "keyDown", value: modifier_value },
          { type: "keyDown", value: key_value },
          { type: "keyUp", value: key_value },
          { type: "keyUp", value: modifier_value }
        ]
      }]
    })
  ensure
    release_actions
  end

  def screenshot
    request(:get, session_path("screenshot"))
  end

  def wait_until(timeout: 10, interval: 0.05)
    deadline = Process.clock_gettime(Process::CLOCK_MONOTONIC) + timeout

    loop do
      value = yield
      return value if value

      if Process.clock_gettime(Process::CLOCK_MONOTONIC) >= deadline
        raise "Condition was not satisfied within #{timeout} seconds"
      end

      sleep interval
    end
  end

  private

  def session_path(suffix = nil)
    raise "WebDriver session has not started" unless @session_id

    suffix ? "/session/#{@session_id}/#{suffix}" : "/session/#{@session_id}"
  end

  def release_actions
    request(:delete, session_path("actions")) if @session_id
  rescue StandardError
    nil
  end

  def request(method, path, body = nil, read_timeout: COMMAND_READ_TIMEOUT)
    uri = URI.join(@endpoint.to_s, path)
    request_class = {
      delete: Net::HTTP::Delete,
      get: Net::HTTP::Get,
      post: Net::HTTP::Post
    }.fetch(method)
    http_request = request_class.new(uri)

    if method == :post || body
      http_request["Content-Type"] = "application/json"
      http_request.body = JSON.generate(body || {})
    end

    response = Net::HTTP.start(uri.host, uri.port, open_timeout: 5, read_timeout: read_timeout) do |http|
      http.request(http_request)
    end
    parsed = response.body.empty? ? {} : JSON.parse(response.body)

    unless response.is_a?(Net::HTTPSuccess)
      message = parsed.dig("value", "message") || response.body
      raise "WebDriver #{method.to_s.upcase} #{path} failed (#{response.code}): #{message}"
    end

    parsed.fetch("value", parsed)
  end
end

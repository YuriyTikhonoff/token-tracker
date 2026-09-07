-- Token Tracker floating overlay for Hammerspoon.
--
-- Shows the token-tracker "Subscription limits" card + daily-tokens chart in
-- an always-on-top panel that follows you across Spaces and floats over other
-- windows -- the thing Übersicht can't do.
--
-- The panel just loads http://127.0.0.1:8765/widget (served by the FastAPI
-- backend, routes/widget.py); all rendering/polling lives in that page.
--
-- Load it from ~/.hammerspoon/init.lua:
--   dofile("/Users/yuritykhonov/Documents/code/personal-monorepo/token-tracker/widgets/hammerspoon/token-tracker.lua")
--
-- Hotkeys (⌘⌥⌃):
--   T  toggle show/hide
--   R  reload the page
--   [  snap to top-left    ]  snap to top-right
--
-- To resize: change SCALE below (0.85 = 85%). It shrinks the window and the
-- page content together. Reload the Hammerspoon config afterwards.

local M = {}

local BACKEND = "http://127.0.0.1:8765"

-- The one knob for size: 1.0 = native, 0.85 = 85%, etc. Scales the window
-- and the page content together (the page reads ?scale= and zooms itself).
local SCALE = 0.5

-- Native (unscaled) content size -- must fit the daily chart's x-axis labels.
local BASE_WIDTH = 560
local BASE_HEIGHT = 560

-- hs.webview.new({h=...}) sizes the *web content area*; macOS adds its ~28pt
-- title bar on top for the outer window. So BASE_HEIGHT is the content height
-- and matches the dashboard's "Widget preview" iframe 1:1 -- tune it there.

-- Re-read the DB this often (seconds).
local POLL_SECONDS = 60
-- Kick a full ingest + /usage snapshot every time the panel loads/reloads, so
-- the numbers are current and not just whatever the last launchd run left.
-- The cached data still paints instantly; this just updates it a beat later.
local REFRESH_ON_LOAD = true

local URL = BACKEND
  .. "/widget?scale=" .. SCALE
  .. "&poll=" .. POLL_SECONDS
  .. (REFRESH_ON_LOAD and "&refresh=1" or "")
local WIDTH = math.floor(BASE_WIDTH * SCALE)
local HEIGHT = math.floor(BASE_HEIGHT * SCALE)
local MARGIN = 16
local HOTKEY_MODS = { "cmd", "alt", "ctrl" }

local webview = nil
local visible = false

local function frameForCorner(corner)
  local screen = hs.screen.mainScreen():frame()
  local x = corner == "topleft" and (screen.x + MARGIN)
    or (screen.x + screen.w - WIDTH - MARGIN)
  return { x = x, y = screen.y + MARGIN, w = WIDTH, h = HEIGHT }
end

local function build()
  if webview then return end

  webview = hs.webview.new(frameForCorner("topright"))
  -- Plain titled window (NOT "utility" -- utility panels auto-hide whenever
  -- Hammerspoon isn't the frontmost app). Draggable by its title bar,
  -- closable, and kept above normal windows by the floating level.
  webview:windowStyle({ "titled", "closable" })
  webview:windowTitle("Token Tracker")
  webview:level(hs.drawing.windowLevels.floating)
  -- Raw NSWindowCollectionBehavior bitmask:
  --   canJoinAllSpaces (1)     -- visible on every Space
  --   stationary (16)          -- doesn't slide during Space-swipe animations
  --   fullScreenAuxiliary (256)-- also shows over a fullscreened app
  webview:behavior(1 + 16 + 256)
  webview:allowTextEntry(false)
  webview:allowGestures(false)
  webview:deleteOnClose(false)
  webview:windowCallback(function(action)
    if action == "closing" then visible = false end
  end)
  webview:url(URL)
end

function M.show()
  build()
  webview:show()
  visible = true
end

function M.hide()
  if webview then webview:hide() end
  visible = false
end

function M.toggle()
  if visible then M.hide() else M.show() end
end

function M.reload()
  if webview then webview:reload() end
end

function M.snap(corner)
  build()
  webview:frame(frameForCorner(corner))
  if not visible then M.show() end
end

hs.hotkey.bind(HOTKEY_MODS, "T", M.toggle)
hs.hotkey.bind(HOTKEY_MODS, "R", M.reload)
hs.hotkey.bind(HOTKEY_MODS, "[", function() M.snap("topleft") end)
hs.hotkey.bind(HOTKEY_MODS, "]", function() M.snap("topright") end)

M.show()

return M

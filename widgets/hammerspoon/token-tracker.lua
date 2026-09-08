-- Token Tracker floating overlay for Hammerspoon.
--
-- Shows the token-tracker "Subscription limits" card + daily-tokens chart in
-- an always-on-top panel that follows you across Spaces and floats over other
-- windows -- the thing Übersicht can't do.
--
-- The panel loads http://127.0.0.1:8765/widget (served by the FastAPI backend,
-- routes/widget.py) for all rendering. Fresh data is driven from here: while
-- the panel is visible an hs.timer POSTs /api/refresh every REFRESH_MINUTES and
-- reloads the page. (The page's own JS timer can't be relied on -- WKWebView
-- suspends it whenever the window is in the background.)
--
-- Load it from ~/.hammerspoon/init.lua:
--   dofile("/Users/yuritykhonov/Documents/code/personal-monorepo/token-tracker/widgets/hammerspoon/token-tracker.lua")
--
-- Hotkeys (⌘⌥⌃):
--   T  toggle show/hide
--   R  refresh + reload now
--   [  snap to top-left    ]  snap to top-right
--
-- To resize: change SCALE below (0.5 = 50%). It shrinks the window and the
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

-- The page re-reads the DB this often (seconds) while it's on screen -- cheap,
-- catches ingest updates between full refreshes.
local POLL_SECONDS = 60

-- How often (minutes) to pull genuinely fresh data: ingest + a `claude -p
-- "/usage"` snapshot via POST /api/refresh. This is driven from Lua, not the
-- page, because WKWebView suspends JS timers while the window is in the
-- background -- an hs.timer keeps running regardless. Only fires while the
-- panel is visible, so a hidden widget costs nothing.
local REFRESH_MINUTES = 3

local URL = BACKEND .. "/widget?scale=" .. SCALE .. "&poll=" .. POLL_SECONDS
local WIDTH = math.floor(BASE_WIDTH * SCALE)
local HEIGHT = math.floor(BASE_HEIGHT * SCALE)
local MARGIN = 16
local HOTKEY_MODS = { "cmd", "alt", "ctrl" }

local webview = nil
local visible = false
local refreshTimer = nil
local refreshing = false

-- POST /api/refresh (ingest + /usage snapshot), then reload the page so the
-- fresh numbers show. Guarded so a slow refresh doesn't stack.
local function refreshNow()
  if refreshing then return end
  refreshing = true
  hs.http.asyncPost(BACKEND .. "/api/refresh", "", {}, function(status)
    refreshing = false
    if webview and visible and status and status >= 200 and status < 500 then
      webview:reload()
    end
  end)
end

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
  refreshNow() -- one fresh pull on open
  if not refreshTimer then
    refreshTimer = hs.timer.doEvery(REFRESH_MINUTES * 60, refreshNow)
  end
end

function M.hide()
  if webview then webview:hide() end
  visible = false
  if refreshTimer then
    refreshTimer:stop()
    refreshTimer = nil
  end
end

function M.toggle()
  if visible then M.hide() else M.show() end
end

function M.reload()
  if not webview then return end
  webview:reload()
  refreshNow()
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

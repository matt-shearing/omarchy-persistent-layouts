.pragma library

function emptyStatus() {
  return {
    ok: false,
    connected: [],
    current: [],
    active: "",
    detected: "",
    candidates: [],
    profiles: [],
    auto: true,
    error: ""
  }
}

function parseStatus(raw) {
  try {
    var data = JSON.parse(String(raw || "").trim())
    if (!data || typeof data !== "object") return emptyStatus()
    return {
      ok: data.ok === true,
      connected: Array.isArray(data.connected) ? data.connected : [],
      current: Array.isArray(data.current) ? data.current : [],
      active: String(data.active || ""),
      detected: String(data.detected || ""),
      candidates: Array.isArray(data.candidates) ? data.candidates : [],
      profiles: Array.isArray(data.profiles) ? data.profiles : [],
      auto: data.auto !== false,
      error: String(data.error || "")
    }
  } catch (e) {
    return emptyStatus()
  }
}

function shortName(fp) {
  var s = String(fp || "")
  var parts = s.split("|")
  if (parts.length === 2) return parts[1]
  return s
}

// A name a human can tell apart from the panel sitting next to it. Two
// displays can report the same make and model, so never rely on that alone:
// prefer the label saved in the profile, and always fall back to something
// carrying the resolution.
function displayLabel(mon) {
  var m = mon || {}
  if (m.label) return String(m.label)
  var base = shortName(String(m.fingerprint || m.name || ""))
  var res = String(m.resolution || "")
  return res ? (base + " · " + res) : base
}

function displayDetail(mon) {
  var m = mon || {}
  var bits = []
  if (m.mode) bits.push(String(m.mode).replace(/@(\d+)\.00$/, "@$1"))
  if (m.scale) bits.push("×" + m.scale)
  if (m.name) bits.push(String(m.name))
  return bits.join("  ")
}

function connectedLabel(status) {
  var cur = (status && status.current) || []
  if (!cur.length) return "No displays"
  var names = []
  for (var i = 0; i < cur.length; i++) names.push(displayLabel(cur[i]))
  return names.join(" · ")
}

function profileHint(p) {
  if (p.applied) return "applied"
  if (p.active) return "active"
  if (p.matches) return "matches now"
  var n = Number(p.outputs) || 0
  return n === 1 ? "1 screen" : (n + " screens")
}

// More than one saved desk describes this exact set of displays, so detection
// alone cannot choose. Clicking one pins it for this set.
function isAmbiguous(status) {
  return ((status && status.candidates) || []).length > 1
}

function pluginDirFromUrl(url) {
  var u = String(url || "")
  if (u.indexOf("file://") === 0) u = u.slice(7)
  return u.replace(/\/$/, "")
}

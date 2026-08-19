.pragma library

function emptyStatus() {
  return {
    ok: false,
    connected: [],
    current: [],
    active: "",
    detected: "",
    profiles: [],
    auto: true
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
      profiles: Array.isArray(data.profiles) ? data.profiles : [],
      auto: data.auto !== false
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

function connectedLabel(status) {
  var cur = (status && status.current) || []
  if (!cur.length) return "No displays"
  var names = []
  for (var i = 0; i < cur.length; i++) {
    var m = cur[i] || {}
    names.push(shortName(m.fingerprint || m.name || ""))
  }
  return names.join(" · ")
}

function profileHint(p) {
  if (p.active) return "active"
  if (p.matches) return "matches"
  var n = Number(p.outputs) || 0
  return n === 1 ? "1 screen" : (n + " screens")
}

function pluginDirFromUrl(url) {
  var u = String(url || "")
  if (u.indexOf("file://") === 0) u = u.slice(7)
  return u.replace(/\/$/, "")
}

import QtQuick
import Quickshell
import Quickshell.Io
import Quickshell.Hyprland

Item {
  id: root

  readonly property string pluginDir: {
    var u = Qt.resolvedUrl(".").toString()
    if (u.indexOf("file://") === 0) u = u.slice(7)
    return u.replace(/\/$/, "")
  }
  readonly property string profileBin: root.pluginDir + "/bin/persistent-layouts"

  function applyDetected() {
    if (applyProc.running) return
    applyProc.command = [root.profileBin, "detect", "--apply", "--json"]
    applyProc.running = true
  }

  function retryApply() {
    applyDetected()
    retry1.restart()
    retry3.restart()
    retry7.restart()
    retry15.restart()
    retry30.restart()
    retry60.restart()
    retry90.restart()
    retry120.restart()
  }

  function onMonitorEvent(event) {
    var name = String(event && event.name ? event.name : "")
    // configreloaded: monitors.lua disables Linux FHD on every reload; re-apply
    // so a dummy-masked Arzopa is driven at 1080p again instead of staying dark.
    if (name.indexOf("monitoradded") === 0 || name.indexOf("monitorremoved") === 0 || name.indexOf("configreloaded") === 0)
      root.retryApply()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) { root.onMonitorEvent(event) }
  }

  Component.onCompleted: root.retryApply()

  Process { id: applyProc }

  // Framework HDMI expansion cards can bounce for a minute after a long s2idle.
  Timer { id: retry1; interval: 1000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry3; interval: 3000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry7; interval: 7000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry15; interval: 15000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry30; interval: 30000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry60; interval: 60000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry90; interval: 90000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry120; interval: 120000; repeat: false; onTriggered: root.applyDetected() }

  Process {
    running: true
    command: [
      "dbus-monitor", "--system",
      "type='signal',sender='org.freedesktop.login1',interface='org.freedesktop.login1.Manager',member='PrepareForSleep'"
    ]
    stdout: SplitParser {
      onRead: function(line) {
        if (String(line).indexOf("boolean false") !== -1)
          root.retryApply()
      }
    }
  }
}

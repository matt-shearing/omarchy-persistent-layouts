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
  }

  function onMonitorEvent(event) {
    var name = String(event && event.name ? event.name : "")
    if (name.indexOf("monitoradded") === 0 || name.indexOf("monitorremoved") === 0)
      root.retryApply()
  }

  Connections {
    target: Hyprland
    function onRawEvent(event) { root.onMonitorEvent(event) }
  }

  Component.onCompleted: root.retryApply()

  Process { id: applyProc }

  Timer { id: retry1; interval: 1000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry3; interval: 3000; repeat: false; onTriggered: root.applyDetected() }
  Timer { id: retry7; interval: 7000; repeat: false; onTriggered: root.applyDetected() }
}

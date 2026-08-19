import QtQuick
import Quickshell
import Quickshell.Io
import qs.Commons
import qs.Ui
import "Model.js" as Model

Panel {
  id: root
  moduleName: "contra.layouts"
  ipcTarget: "contra.layouts"
  manageIpc: false

  property var status: Model.emptyStatus()
  property bool cursorActive: false
  property int focusIndex: 0

  readonly property string pluginDir: Model.pluginDirFromUrl(Qt.resolvedUrl("."))
  readonly property string profileBin: root.pluginDir + "/bin/persistent-layouts"
  readonly property int controlCount: root.status.profiles.length + 2

  function refresh() {
    if (!statusProc.running) statusProc.running = true
  }

  function applyProfile(id) {
    if (!id || actionProc.running) return
    actionProc.command = [root.profileBin, "apply", id]
    actionProc.running = true
  }

  function saveCurrent() {
    if (actionProc.running) return
    var id = root.status.detected || root.status.active || ""
    if (id)
      actionProc.command = [root.profileBin, "save", id, "--update-matching"]
    else
      actionProc.command = [root.profileBin, "save", "--update-matching"]
    actionProc.running = true
  }

  function setAuto(on) {
    if (actionProc.running) return
    actionProc.command = [root.profileBin, "auto", on ? "on" : "off"]
    actionProc.running = true
  }

  function activateFocused() {
    if (focusIndex < root.status.profiles.length)
      applyProfile(root.status.profiles[focusIndex].id)
    else if (focusIndex === root.status.profiles.length)
      saveCurrent()
    else
      setAuto(!root.status.auto)
  }

  IpcHandler {
    target: "contra.layouts"
    function open() { root.open() }
    function close() { root.close() }
    function show() { root.open() }
    function hide() { root.close() }
    function toggle() { root.toggle() }
  }

  onOpenedChanged: if (opened) refresh()

  Process {
    id: statusProc
    command: [root.profileBin, "status"]
    stdout: StdioCollector {
      waitForEnd: true
      onStreamFinished: root.status = Model.parseStatus(text)
    }
  }

  Process {
    id: actionProc
    onExited: Qt.callLater(function() { root.refresh() })
  }

  Timer { interval: 4000; running: true; repeat: true; onTriggered: root.refresh() }
  Timer { interval: 1500; running: root.opened; repeat: true; onTriggered: root.refresh() }

  Component.onCompleted: refresh()

  implicitWidth: button.implicitWidth
  implicitHeight: button.implicitHeight

  BarIconButton {
    id: button
    anchors.fill: parent
    bar: root.bar
    text: "󰡃"
    tooltipText: {
      if (root.status.error) return "Persistent Layouts · apply failed"
      var name = ""
      for (var i = 0; i < root.status.profiles.length; i++) {
        if (root.status.profiles[i].active) { name = root.status.profiles[i].name; break }
      }
      return name ? ("Persistent Layouts · " + name) : ("Persistent Layouts · " + Model.connectedLabel(root.status))
    }
    onPressed: function(b) {
      if (b === Qt.RightButton) {
        if (root.status.detected) root.applyProfile(root.status.detected)
        else root.toggle()
      } else {
        root.toggle()
      }
    }
  }

  KeyboardPanel {
    id: panel
    anchorItem: button
    owner: root
    bar: root.bar
    open: root.opened
    focusTarget: keyCatcher
    contentWidth: panel.fittedContentWidth(Style.space(380))
    contentHeight: panel.fittedContentHeight(column.implicitHeight)

    PanelKeyCatcher {
      id: keyCatcher
      anchors.fill: parent
      onMoveRequested: function(dx, dy) {
        root.cursorActive = true
        var d = dx !== 0 ? dx : dy
        root.focusIndex = Math.max(0, Math.min(root.controlCount - 1, root.focusIndex + d))
      }
      onActivateRequested: if (root.cursorActive) root.activateFocused()
      onCloseRequested: root.close()
      onTabRequested: function(direction) { root.switchPanel(direction) }

      Column {
        id: column
        anchors.left: parent.left
        anchors.right: parent.right
        anchors.top: parent.top
        spacing: Style.space(12)

        Text {
          text: "Persistent Layouts"
          color: root.bar.foreground
          font.family: root.bar.fontFamily
          font.pixelSize: Style.font.title
          font.bold: true
        }

        PanelSeparator { foreground: root.bar.foreground }

        // Connected displays, one line each. Two panels can report the same
        // make and model, so each row carries its own resolution and output.
        Column {
          width: parent.width
          spacing: Style.space(6)

          Text {
            visible: root.status.current.length === 0
            text: "No displays"
            color: root.bar.foreground
            opacity: 0.65
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
          }

          Repeater {
            model: root.status.current
            Column {
              required property var modelData
              width: parent.width
              spacing: 0
              Text {
                width: parent.width
                text: Model.displayLabel(modelData)
                color: root.bar.foreground
                font.family: root.bar.fontFamily
                font.pixelSize: Style.font.bodySmall
                elide: Text.ElideRight
              }
              Text {
                width: parent.width
                text: Model.displayDetail(modelData)
                color: root.bar.foreground
                opacity: 0.55
                font.family: root.bar.fontFamily
                font.pixelSize: Style.font.bodySmall
                elide: Text.ElideRight
              }
            }
          }
        }

        PanelSeparator { foreground: root.bar.foreground }

        Column {
          width: parent.width
          spacing: Style.space(6)

          Text {
            visible: root.status.profiles.length === 0
            width: parent.width
            text: "Arrange the screens, then save this desk as a named layout."
            color: root.bar.foreground
            opacity: 0.65
            wrapMode: Text.WordWrap
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
          }

          Repeater {
            model: root.status.profiles
            Button {
              required property var modelData
              required property int index
              width: parent.width
              text: modelData.name + "  ·  " + Model.profileHint(modelData)
              fontSize: Style.font.bodySmall
              foreground: root.bar.foreground
              fontFamily: root.bar.fontFamily
              horizontalPadding: Style.spacing.controlPaddingX
              verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
              bordered: true
              active: modelData.applied === true || modelData.matches === true
              hasCursor: root.cursorActive && root.focusIndex === index
              onClicked: root.applyProfile(modelData.id)
              onHovered: function(h) { if (h) { root.cursorActive = true; root.focusIndex = index } }
            }
          }

          Text {
            visible: Model.isAmbiguous(root.status)
            width: parent.width
            text: "More than one layout fits these displays. Click the one you want — it stays picked for this set."
            color: root.bar.foreground
            opacity: 0.65
            wrapMode: Text.WordWrap
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
          }

          Text {
            visible: root.status.error !== ""
            width: parent.width
            text: "Apply failed — " + root.status.error
            color: root.bar.foreground
            wrapMode: Text.WordWrap
            font.family: root.bar.fontFamily
            font.pixelSize: Style.font.bodySmall
          }
        }

        Button {
          width: parent.width
          text: "Save current layout"
          fontSize: Style.font.bodySmall
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
          horizontalPadding: Style.spacing.controlPaddingX
          verticalPadding: Style.spacing.controlPaddingY + Style.space(2)
          bordered: true
          hasCursor: root.cursorActive && root.focusIndex === root.status.profiles.length
          onClicked: root.saveCurrent()
          onHovered: function(h) {
            if (h) {
              root.cursorActive = true
              root.focusIndex = root.status.profiles.length
            }
          }
        }

        Toggle {
          width: parent.width
          label: "Apply matching layout on plug-in"
          description: "Restores a saved desk when the same screens connect."
          checked: root.status.auto === true
          foreground: root.bar.foreground
          fontFamily: root.bar.fontFamily
          hasCursor: root.cursorActive && root.focusIndex === root.status.profiles.length + 1
          onClicked: root.setAuto(!root.status.auto)
          onHovered: function(h) {
            if (h) {
              root.cursorActive = true
              root.focusIndex = root.status.profiles.length + 1
            }
          }
        }
      }
    }
  }
}

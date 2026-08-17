#!/usr/bin/env python3
"""Do - a tiny task-capture popup for Omarchy / Hyprland.

Runs as one resident process. The popup is a wlr-layer-shell surface, so the
compositor keeps it above normal windows without any tiling or workspace
involvement. Toggling is a D-Bus action call, which is why it feels instant.
"""

from __future__ import annotations

import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path


def _ensure_layer_shell_preload() -> None:
    """gtk4-layer-shell must be loaded before libwayland-client.

    Python imports them the other way round, so re-exec ourselves once with the
    library preloaded. Without this the popup falls back to a normal window.
    """
    if os.environ.get("DO_PRELOADED") == "1":
        return
    import ctypes.util

    lib = ctypes.util.find_library("gtk4-layer-shell")
    env = dict(os.environ, DO_PRELOADED="1")
    if lib:
        env["LD_PRELOAD"] = ":".join(filter(None, [lib, os.environ.get("LD_PRELOAD", "")]))
    try:
        os.execve(sys.executable, [sys.executable, os.path.abspath(__file__), *sys.argv[1:]], env)
    except OSError as exc:  # keep running unstyled rather than not at all
        print(f"do: could not re-exec with layer-shell preloaded: {exc}", file=sys.stderr)


_ensure_layer_shell_preload()

import gi  # noqa: E402

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
gi.require_version("Gtk4LayerShell", "1.0")

from gi.repository import Gdk, Gio, GLib, Gtk, Pango  # noqa: E402
from gi.repository import Gtk4LayerShell as LayerShell  # noqa: E402

APP_ID = "org.omarchy.Do"
NAMESPACE = "do"
DATA_DIR = Path(GLib.get_user_data_dir()) / "do"
TASKS_FILE = DATA_DIR / "tasks.json"
STYLE_FILE = Path(__file__).resolve().parent / "style.css"

CARD_WIDTH = 450
SHADOW_MARGIN = 18  # transparent gutter the card's drop shadow is drawn into
LIST_MAX_HEIGHT = 344  # keeps the whole popup within ~400-500px tall
# Waybar's own margin-right, so the card's right edge lines up with the bar's
# (and so with the checkmark button, which is the last module in it).
BAR_EDGE_GAP = 10

DEBUG = os.environ.get("DO_DEBUG") == "1"


def log(*args: object) -> None:
    if DEBUG:
        print("do:", *args, file=sys.stderr, flush=True)


def utcnow() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds").replace("+00:00", "Z")


class Store:
    """The task list, persisted as JSON and written atomically."""

    def __init__(self, path: Path = TASKS_FILE) -> None:
        self.path = path
        self.tasks: list[dict] = []
        self.load()

    # -- reading -----------------------------------------------------------

    def load(self) -> None:
        try:
            raw = json.loads(self.path.read_text("utf-8"))
        except FileNotFoundError:
            return
        except (OSError, ValueError) as exc:
            # Never silently overwrite something we failed to parse.
            print(f"do: unreadable {self.path}: {exc}", file=sys.stderr)
            self._quarantine()
            return

        tasks = raw.get("tasks") if isinstance(raw, dict) else raw
        if not isinstance(tasks, list):
            return

        for item in tasks:
            if not isinstance(item, dict) or not isinstance(item.get("title"), str):
                continue
            # Unknown keys are kept as-is so future fields survive this version.
            item.setdefault("id", uuid.uuid4().hex)
            item.setdefault("done", False)
            item.setdefault("created_at", utcnow())
            item.setdefault("completed_at", None)
            item["done"] = bool(item["done"])
            self.tasks.append(item)

    def _quarantine(self) -> None:
        try:
            self.path.rename(self.path.with_name(f"{self.path.name}.corrupt.{int(time.time())}"))
        except OSError:
            pass

    # -- writing -----------------------------------------------------------

    def save(self) -> None:
        """Write via temp file + fsync + rename, so a crash can't truncate data."""
        payload = json.dumps({"version": 1, "tasks": self.tasks}, indent=2, ensure_ascii=False)
        tmp = self.path.with_name(f".{self.path.name}.tmp.{os.getpid()}")
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
            with os.fdopen(fd, "w", encoding="utf-8") as fh:
                fh.write(payload + "\n")
                fh.flush()
                os.fsync(fh.fileno())
            os.replace(tmp, self.path)
            dir_fd = os.open(self.path.parent, os.O_RDONLY)
            try:
                os.fsync(dir_fd)
            finally:
                os.close(dir_fd)
        except OSError as exc:
            print(f"do: save failed: {exc}", file=sys.stderr)
            try:
                tmp.unlink()
            except OSError:
                pass

    # -- mutations ---------------------------------------------------------

    def add(self, title: str) -> dict | None:
        title = title.strip()
        if not title:
            return None
        task = {
            "id": uuid.uuid4().hex,
            "title": title,
            "done": False,
            "created_at": utcnow(),
            "completed_at": None,
        }
        self.tasks.append(task)
        self.save()
        return task

    def get(self, task_id: str) -> dict | None:
        return next((t for t in self.tasks if t["id"] == task_id), None)

    def set_done(self, task_id: str, done: bool) -> None:
        task = self.get(task_id)
        if task is None or task["done"] == done:
            return
        task["done"] = done
        task["completed_at"] = utcnow() if done else None
        self.save()

    def rename(self, task_id: str, title: str) -> None:
        task = self.get(task_id)
        if task is None or task["title"] == title:
            return
        task["title"] = title
        self.save()

    def remove(self, task_id: str) -> None:
        before = len(self.tasks)
        self.tasks = [t for t in self.tasks if t["id"] != task_id]
        if len(self.tasks) != before:
            self.save()

    # -- ordering ----------------------------------------------------------

    def active(self) -> list[dict]:
        """Oldest first, so newly captured tasks land at the bottom."""
        return [t for t in self.tasks if not t["done"]]

    def completed(self) -> list[dict]:
        """Most recently finished first."""
        return sorted(
            (t for t in self.tasks if t["done"]),
            key=lambda t: t.get("completed_at") or "",
            reverse=True,
        )


class TaskRow(Gtk.Box):
    """One task: a round checkbox, an inline-editable title, a quiet delete."""

    def __init__(self, task: dict, popup: "Popup") -> None:
        super().__init__(orientation=Gtk.Orientation.HORIZONTAL, spacing=0)
        self.task = task
        self.popup = popup
        self.editing = False

        self.add_css_class("task-row")
        if task["done"]:
            self.add_css_class("done")
        self.set_focusable(True)

        self.check = Gtk.Button(focusable=False, valign=Gtk.Align.START)
        self.check.add_css_class("check")
        self.check.set_tooltip_text("Toggle complete")
        mark = Gtk.Image.new_from_icon_name("object-select-symbolic")
        mark.set_pixel_size(10)
        mark.add_css_class("check-mark")
        self.check.set_child(mark)
        self.check.connect("clicked", self._on_check_clicked)
        self.append(self.check)

        self.stack = Gtk.Stack(hexpand=True, hhomogeneous=False)
        self.stack.set_transition_type(Gtk.StackTransitionType.NONE)

        self.label = Gtk.Label(label=task["title"], xalign=0.0, valign=Gtk.Align.CENTER)
        self.label.add_css_class("task-title")
        self.label.set_wrap(True)
        self.label.set_wrap_mode(Pango.WrapMode.WORD_CHAR)  # Pango's, not Gtk.WrapMode
        # Ask for one character, so a long title wraps into whatever width the
        # card gives it rather than stretching the popup.
        self.label.set_max_width_chars(1)
        self.stack.add_named(self.label, "view")

        self.entry = Gtk.Entry(text=task["title"], has_frame=False)
        self.entry.add_css_class("task-edit")
        # An entry sizes itself to its text; pin it so a long task can't widen the popup.
        self.entry.set_width_chars(1)
        self.entry.set_max_width_chars(1)
        self.entry.connect("activate", lambda *_: self.commit_edit())
        edit_keys = Gtk.EventControllerKey()
        edit_keys.connect("key-pressed", self._on_edit_key)
        self.entry.add_controller(edit_keys)
        focus = Gtk.EventControllerFocus()
        focus.connect("leave", lambda *_: self.commit_edit())
        self.entry.add_controller(focus)
        self.stack.add_named(self.entry, "edit")
        self.append(self.stack)

        self.delete = Gtk.Button(focusable=False, valign=Gtk.Align.START)
        self.delete.add_css_class("row-delete")
        self.delete.set_child(Gtk.Image.new_from_icon_name("window-close-symbolic"))
        self.delete.set_tooltip_text("Delete task")
        self.delete.connect("clicked", lambda *_: self.popup.delete_task(self.task["id"]))
        self.append(self.delete)

        click = Gtk.GestureClick()
        click.connect("released", self._on_title_clicked)
        self.label.add_controller(click)

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_row_key)
        self.add_controller(keys)

    # -- editing -----------------------------------------------------------

    def start_edit(self) -> None:
        if self.editing:
            return
        self.editing = True
        self.entry.set_text(self.task["title"])
        self.stack.set_visible_child_name("edit")
        self.entry.grab_focus()
        self.entry.set_position(-1)

    def commit_edit(self) -> None:
        if not self.editing:
            return
        self.editing = False
        title = self.entry.get_text().strip()
        self.stack.set_visible_child_name("view")
        if not title:
            # Emptying the title is not a delete - only the x button removes a
            # task. Treat it as a no-op edit and keep what was there.
            self.entry.set_text(self.task["title"])
            self.grab_focus()
            return
        self.popup.store.rename(self.task["id"], title)
        self.task["title"] = title
        self.label.set_text(title)

    def cancel_edit(self) -> None:
        if not self.editing:
            return
        self.editing = False
        self.entry.set_text(self.task["title"])
        self.stack.set_visible_child_name("view")
        self.grab_focus()

    # -- events ------------------------------------------------------------

    def _on_check_clicked(self, _button: Gtk.Button) -> None:
        # Mouse path: hand focus back to the input so typing continues.
        self.popup.toggle_task(self.task["id"], refocus_input=True)

    def _on_title_clicked(self, gesture: Gtk.GestureClick, n_press: int, x: float, y: float) -> None:
        if n_press == 1:
            self.start_edit()

    def _on_edit_key(self, _c: Gtk.EventControllerKey, keyval: int, _kc: int, _st: Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            self.cancel_edit()
            return True
        return False

    def _on_row_key(self, _c: Gtk.EventControllerKey, keyval: int, _kc: int, state: Gdk.ModifierType) -> bool:
        if self.editing:
            return False
        if keyval in (Gdk.KEY_space, Gdk.KEY_KP_Space):
            self.popup.toggle_task(self.task["id"], refocus_input=False)
            return True
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter):
            self.start_edit()
            return True
        if keyval == Gdk.KEY_Delete:
            # Delete only - Backspace is too easy to hit while arrowing around,
            # and there is no undo.
            self.popup.delete_task(self.task["id"])
            return True
        if keyval in (Gdk.KEY_Down, Gdk.KEY_Up):
            self.popup.move_focus(self, forward=keyval == Gdk.KEY_Down)
            return True
        return False


class Popup(Gtk.Window):
    """The layer-shell surface itself."""

    def __init__(self, app: "DoApp", store: Store) -> None:
        super().__init__(application=app)
        self.store = store
        self.rows: list[TaskRow] = []

        self.set_default_size(CARD_WIDTH + 2 * SHADOW_MARGIN, -1)
        self.set_resizable(False)
        self.add_css_class("do-window")

        self._init_layer_shell()
        self._build_ui()

        keys = Gtk.EventControllerKey()
        keys.connect("key-pressed", self._on_key)
        self.add_controller(keys)

        self.connect("close-request", self._on_close_request)

    def _init_layer_shell(self) -> None:
        LayerShell.init_for_window(self)
        LayerShell.set_namespace(self, NAMESPACE)
        LayerShell.set_layer(self, LayerShell.Layer.OVERLAY)
        # Top-right, so it drops out of the checkmark button rather than the
        # middle of the screen. Anchoring beats a computed x: it stays correct
        # on any resolution and follows the focused monitor.
        LayerShell.set_anchor(self, LayerShell.Edge.TOP, True)
        LayerShell.set_anchor(self, LayerShell.Edge.RIGHT, True)
        LayerShell.set_margin(self, LayerShell.Edge.TOP, 0)
        LayerShell.set_margin(self, LayerShell.Edge.RIGHT, 0)
        # Zero (not -1) means: don't reserve space, but stay clear of whatever
        # already does - i.e. sit directly under the top bar, whatever its height.
        LayerShell.set_exclusive_zone(self, 0)
        # Hyprland does not hand keyboard focus to ON_DEMAND layers when they
        # map, and waiting for a click would defeat the point. EXCLUSIVE gets
        # the caret into the input the instant the surface appears.
        LayerShell.set_keyboard_mode(self, LayerShell.KeyboardMode.EXCLUSIVE)

    # -- layout ------------------------------------------------------------

    def _build_ui(self) -> None:
        outer = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        outer.set_margin_top(SHADOW_MARGIN // 2)
        outer.set_margin_bottom(SHADOW_MARGIN)
        outer.set_margin_start(SHADOW_MARGIN)
        # Narrower on the right so the card lands flush with the bar's edge;
        # the shadow points mostly downwards, so it loses little here.
        outer.set_margin_end(BAR_EDGE_GAP)

        card = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        card.add_css_class("card")
        card.set_size_request(CARD_WIDTH - 2, -1)  # size request excludes the 1px border

        header = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        header.add_css_class("header")
        title = Gtk.Label(label="Tasks", xalign=0.0, hexpand=True)
        title.add_css_class("header-title")
        header.append(title)
        self.count = Gtk.Label(xalign=1.0)
        self.count.add_css_class("header-count")
        header.append(self.count)
        card.append(header)

        self.scroller = Gtk.ScrolledWindow(
            hscrollbar_policy=Gtk.PolicyType.NEVER,
            vscrollbar_policy=Gtk.PolicyType.AUTOMATIC,
            propagate_natural_height=True,
            max_content_height=LIST_MAX_HEIGHT,
        )
        self.scroller.add_css_class("list-scroll")
        self.list = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        self.list.add_css_class("list")
        self.scroller.set_child(self.list)
        card.append(self.scroller)

        self.empty = Gtk.Label(label="Nothing to do")
        self.empty.add_css_class("empty")
        card.append(self.empty)

        input_row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        input_row.add_css_class("input-row")
        self.bullet = Gtk.Image.new_from_icon_name("list-add-symbolic")
        self.bullet.set_pixel_size(12)
        self.bullet.add_css_class("input-bullet")
        input_row.append(self.bullet)

        self.entry = Gtk.Entry(
            placeholder_text="Add a task...",
            has_frame=False,
            hexpand=True,
        )
        self.entry.add_css_class("input")
        self.entry.set_width_chars(1)
        self.entry.set_max_width_chars(1)
        self.entry.connect("activate", self._on_entry_activate)
        entry_keys = Gtk.EventControllerKey()
        entry_keys.connect("key-pressed", self._on_entry_key)
        self.entry.add_controller(entry_keys)
        input_row.append(self.entry)
        card.append(input_row)

        outer.append(card)
        self.set_child(outer)

    # -- rendering ---------------------------------------------------------

    def refresh(self, focus_task_id: str | None = None) -> None:
        while (child := self.list.get_first_child()) is not None:
            self.list.remove(child)
        self.rows = []

        active, completed = self.store.active(), self.store.completed()

        for task in active:
            self._append_row(task)

        if completed:
            if active:
                sep = Gtk.Label(label="Completed", xalign=0.0)
                sep.add_css_class("section")
                self.list.append(sep)
            for task in completed:
                self._append_row(task)

        has_tasks = bool(self.store.tasks)
        self.scroller.set_visible(has_tasks)
        self.empty.set_visible(not has_tasks)
        self.count.set_text(str(len(active)) if active else "")

        if focus_task_id is not None:
            for row in self.rows:
                if row.task["id"] == focus_task_id:
                    row.grab_focus()
                    return
        # Otherwise the input stays the resting place for focus.
        self.focus_input()

    def _append_row(self, task: dict) -> None:
        row = TaskRow(task, self)
        self.list.append(row)
        self.rows.append(row)

    def focus_input(self) -> None:
        self.entry.grab_focus()

    def _scroll_to_bottom(self) -> None:
        adj = self.scroller.get_vadjustment()
        adj.set_value(adj.get_upper() - adj.get_page_size())
        return GLib.SOURCE_REMOVE

    # -- actions -----------------------------------------------------------

    def add_task(self) -> None:
        text = self.entry.get_text()
        if not text.strip():
            return
        self.store.add(text)
        self.entry.set_text("")
        self.refresh()
        self.focus_input()
        GLib.idle_add(self._scroll_to_bottom)

    def toggle_task(self, task_id: str, refocus_input: bool) -> None:
        task = self.store.get(task_id)
        if task is None:
            return
        self.store.set_done(task_id, not task["done"])
        self.refresh(focus_task_id=None if refocus_input else task_id)

    def delete_task(self, task_id: str) -> None:
        self.store.remove(task_id)
        self.refresh()

    def move_focus(self, row: TaskRow, forward: bool) -> None:
        try:
            i = self.rows.index(row)
        except ValueError:
            return
        j = i + (1 if forward else -1)
        if j < 0:
            self.focus_input()
        elif j < len(self.rows):
            self.rows[j].grab_focus()

    # -- events ------------------------------------------------------------

    def _on_entry_activate(self, _entry: Gtk.Entry) -> None:
        self.add_task()

    def _on_entry_key(self, _c: Gtk.EventControllerKey, keyval: int, _kc: int, state: Gdk.ModifierType) -> bool:
        if keyval in (Gdk.KEY_Return, Gdk.KEY_KP_Enter) and state & Gdk.ModifierType.CONTROL_MASK:
            self.add_task()
            return True
        if keyval == Gdk.KEY_Down and self.rows:
            self.rows[0].grab_focus()
            return True
        return False

    def _on_key(self, _c: Gtk.EventControllerKey, keyval: int, _kc: int, _st: Gdk.ModifierType) -> bool:
        if keyval == Gdk.KEY_Escape:
            focused = self.get_focus()
            row = focused.get_ancestor(TaskRow) if focused else None
            if isinstance(row, TaskRow) and row.editing:
                row.cancel_edit()
            elif isinstance(row, TaskRow):
                self.focus_input()
            else:
                self.hide_popup()
            return True
        return False

    # Closing is deliberate only - Escape, Super + D, or the bar button. The
    # exclusive keyboard grab means a click outside never reaches us, so there
    # is no dependable click-away signal to hook; guessing at one would risk
    # the popup vanishing mid-sentence.

    def _on_close_request(self, _window: Gtk.Window) -> bool:
        self.hide_popup()
        return True  # never destroy; the process stays resident

    # -- visibility --------------------------------------------------------

    def show_popup(self) -> None:
        if self.get_visible():
            self.focus_input()
            return
        self.store.tasks = []
        self.store.load()  # pick up edits made while we were hidden
        self.entry.set_text("")
        self.refresh()
        self.present()
        self.focus_input()
        GLib.idle_add(self._after_present)
        log("shown")

    def _after_present(self) -> bool:
        self.focus_input()
        # Open at the top of the list; only adding a task scrolls to the bottom.
        self.scroller.get_vadjustment().set_value(0)
        log("active =", self.is_active(), "focus =", type(self.get_focus()).__name__)
        return GLib.SOURCE_REMOVE

    def hide_popup(self) -> None:
        focused = self.get_focus()
        row = focused.get_ancestor(TaskRow) if focused else None
        if isinstance(row, TaskRow) and row.editing:
            row.commit_edit()
        self.set_visible(False)
        log("hidden")

    def toggle_popup(self) -> None:
        if self.get_visible():
            self.hide_popup()
        else:
            self.show_popup()


class DoApp(Gtk.Application):
    def __init__(self) -> None:
        super().__init__(
            application_id=APP_ID,
            flags=Gio.ApplicationFlags.HANDLES_COMMAND_LINE,
        )
        self.popup: Popup | None = None
        self.add_main_option(
            "daemon", 0, GLib.OptionFlags.NONE, GLib.OptionArg.NONE,
            "Start resident without showing the popup", None,
        )
        for name, handler in (
            ("toggle", lambda *_: self._with_popup(Popup.toggle_popup)),
            ("show", lambda *_: self._with_popup(Popup.show_popup)),
            ("hide", lambda *_: self._with_popup(Popup.hide_popup)),
            ("quit", lambda *_: self.quit()),
        ):
            action = Gio.SimpleAction.new(name, None)
            action.connect("activate", handler)
            self.add_action(action)

    def _with_popup(self, method) -> None:
        if self.popup is not None:
            method(self.popup)

    def do_startup(self) -> None:
        Gtk.Application.do_startup(self)
        self._load_css()
        DATA_DIR.mkdir(parents=True, exist_ok=True)
        self.popup = Popup(self, Store())
        self.hold()  # stay alive with no visible window

    def _load_css(self) -> None:
        provider = Gtk.CssProvider()
        try:
            provider.load_from_path(str(STYLE_FILE))
        except GLib.Error as exc:
            print(f"do: css: {exc}", file=sys.stderr)
            return
        Gtk.StyleContext.add_provider_for_display(
            Gdk.Display.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
        )

    def do_command_line(self, command_line: Gio.ApplicationCommandLine) -> int:
        options = command_line.get_options_dict()
        if not options.contains("daemon"):
            self._with_popup(Popup.toggle_popup)
        return 0

    def do_activate(self) -> None:
        self._with_popup(Popup.toggle_popup)


def main() -> int:
    return DoApp().run(sys.argv)


if __name__ == "__main__":
    sys.exit(main())

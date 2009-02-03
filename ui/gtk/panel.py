# vim:set et sts=4 sw=4:
#
# ibus - The Input Bus
#
# Copyright(c) 2007-2008 Huang Peng <shawn.p.huang@gmail.com>
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 2 of the License, or(at your option) any later version.
#
# This library is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this program; if not, write to the
# Free Software Foundation, Inc., 59 Temple Place, Suite 330,
# Boston, MA  02111-1307  USA

import gtk
import gtk.gdk as gdk
import gobject
import ibus
import icon as _icon
import os
import sys
import signal
from os import path
from ibus import interface
from languagebar import LanguageBar
from candidatepanel import CandidatePanel

from gettext import dgettext
_  = lambda a : dgettext("ibus", a)
N_ = lambda a : a

def show_uri(screen, link):
    try:
        gtk.show_uri(screen, link, 0)
    except:
        print >> sys.stderr, "pygtk do not support show_uri"

def url_hook(about, link, user_data):
    show_uri(about.get_screen(), link)

def email_hook(about, email, user_data):
    show_uri(about.get_screen(), "mailto:%s" % email)

gtk.about_dialog_set_url_hook(url_hook, None)
gtk.about_dialog_set_email_hook(email_hook, None)

class Panel(ibus.PanelBase):
    def __init__ (self, bus):
        super(Panel, self).__init__(bus)
        self.__bus = bus
        self.__focus_ic = None
        self.__setup_pid = 0
        self.__prefix = os.getenv("IBUS_PREFIX")
        self.__data_dir = path.join(self.__prefix, "share", "ibus")
        self.__icons_dir = path.join(self.__data_dir, "icons")
        self.__ibus_icon = path.join(self.__icons_dir, "ibus.svg")
        self.__setup_cmd = path.join(self.__prefix, "bin", "ibus-setup")

        # hanlder signal
        signal.signal(signal.SIGCHLD, self.__sigchld_cb)

        # connect bus signal
        self.__bus.connect("config-value-changed", self.__config_value_changed_cb)
        self.__bus.connect("config-reloaded", self.__config_reloaded_cb)
        self.__bus.config_add_watch("panel")

        # add icon search path
        icon_theme = gtk.icon_theme_get_default()
        dir = path.dirname(__file__)
        icondir = path.join(dir, "..", "icons")
        icon_theme.prepend_search_path(icondir)

        self.__language_bar = LanguageBar()
        self.__language_bar.connect("property-activate",
                        lambda widget, prop_name, prop_state: self.property_activate(prop_name, prop_state))
        self.__language_bar.connect("get-im-menu",
                        self.__get_im_menu_cb)
        self.__language_bar.focus_out()
        self.__language_bar.show_all()

        self.__candidate_panel = CandidatePanel()
        self.__candidate_panel.connect("cursor-up",
                        lambda widget: self.cursor_up())
        self.__candidate_panel.connect("cursor-down",
                        lambda widget: self.cursor_down())

        self.__status_icon = gtk.StatusIcon()
        self.__status_icon.connect("popup-menu", self.__status_icon_popup_menu_cb)
        self.__status_icon.connect("activate", self.__status_icon_activate_cb)
        self.__status_icon.set_from_file(self.__ibus_icon)
        self.__status_icon.set_tooltip(_("iBus - Running"))
        self.__status_icon.set_visible(True)

        self.__config_load_lookup_table_orientation()
        self.__config_load_auto_hide()
        self.__config_load_custom_font()
        self.__bus.request_name(ibus.panel.IBUS_PANEL_NAME, 0)

    def set_cursor_location(self, x, y, w, h):
        self.__candidate_panel.set_cursor_location(x + w, y + h)

    def update_preedit(self, text, attrs, cursor_pos, visible):
        self.__candidate_panel.update_preedit(text, attrs, cursor_pos, visible)

    def show_preedit(self):
        self.__candidate_panel.show_preedit()

    def hide_preedit(self):
        self.__candidate_panel.hide_preedit()

    def update_aux_string(self, text, attrs, visible):
        self.__candidate_panel.update_aux_string(text, attrs, visible)

    def show_aux_string(self):
        self.__candidate_panel.show_aux_string()

    def hide_aux_string(self):
        self.__candidate_panel.hide_aux_string()

    def update_lookup_table(self, lookup_table, visible):
        self.__candidate_panel.update_lookup_table(lookup_table, visible)

    def show_lookup_table(self):
        self.__candidate_panel.show_lookup_table()

    def hide_lookup_table(self):
        self.__candidate_panel.hide_lookup_table()

    def page_up_lookup_table(self):
        self.__candidate_panel.page_up_lookup_table()

    def page_down_lookup_table(self):
        self.__candidate_panel.page_down_lookup_table()

    def cursor_up_lookup_table(self):
        self.__candidate_panel.cursor_up_lookup_table()

    def cursor_down_lookup_table(self):
        self.__candidate_panel.cursor_down_lookup_table()

    def show_candidate_window(self):
        self.__candidate_panel.show_all()

    def hide_candidate_window(self):
        self.__candidate_panel.hide_all()

    def show_language_bar(self):
        self.__language_bar.show_all()

    def hide_language_bar(self):
        self.__language_bar.hide_all()

    def register_properties(self, props):
        self.__language_bar.register_properties(props)

    def update_property(self, prop):
        self.__language_bar.update_property(prop)

    def get_status_icon(self):
        return self.__status_icon

    def __set_im_icon(self, icon_name):
        self.__language_bar.set_im_icon(icon_name)
        if icon_name.startswith("/"):
            self.__status_icon.set_from_file(icon_name)
        else:
            self.__status_icon.set_from_icon_name(icon_name)

    def focus_in(self, ic):
        self.reset()
        self.__focus_ic = ic

        factory, enabled = self.__bus.get_input_context_states(ic)
        self.__language_bar.set_enabled(enabled)

        if factory == "" or not enabled:
            self.__set_im_icon(self.__ibus_icon)
        else:
            name, lang, icon, authors, credits = self.__bus.get_factory_info(factory)
            self.__set_im_icon(icon)
        self.__language_bar.focus_in()

    def focus_out(self, ic):
        self.reset()
        if self.__focus_ic == ic:
            self.__focus_ic = None
            self.__language_bar.focus_out()
            self.__set_im_icon(self.__ibus_icon)

    def states_changed(self):
        if not self.__focus_ic:
            return
        factory, enabled = self.__bus.get_input_context_states(self.__focus_ic)
        self.__language_bar.set_enabled(enabled)
        if enabled == False or not factory:
            self.__set_im_icon(self.__ibus_icon)
        else:
            name, lang, icon, authors, credits = self.__bus.get_factory_info(factory)
            self.__set_im_icon(icon)

    def reset(self):
        self.__candidate_panel.reset()
        self.__language_bar.reset()

    def start_setup(self):
        self.__start_setup()

    def do_destroy(self):
        gtk.main_quit()

    def __config_load_lookup_table_orientation(self):
        value = self.__bus.config_get_value("panel", "lookup_table_orientation", 0)
        if value != 0 and value != 1:
            value = 0
        if value == 0:
            self.__candidate_panel.set_orientation(gtk.ORIENTATION_HORIZONTAL)
        else:
            self.__candidate_panel.set_orientation(gtk.ORIENTATION_VERTICAL)

    def __config_load_auto_hide(self):
        auto_hide = self.__bus.config_get_value("panel", "auto_hide", False)
        self.__language_bar.set_auto_hide(auto_hide)

    def __config_load_custom_font(self):
        use_custom_font = self.__bus.config_get_value("panel", "use_custom_font", False)
        font_name = gtk.settings_get_default().get_property("gtk-font-name")
        font_name = unicode(font_name, "utf-8")
        custom_font =  self.__bus.config_get_value("panel", "custom_font", font_name)
        style_string = 'style "custom-font" { font_name="%s" }\n' \
            'class "IBusPanelLabel" style "custom-font"\n'
        if use_custom_font:
            style_string = style_string % custom_font
            gtk.rc_parse_string(style_string)
        else:
            style_string = style_string % ""
            gtk.rc_parse_string(style_string)

        settings = gtk.settings_get_default()
        gtk.rc_reset_styles(settings)

    def __config_value_changed_cb(self, bus, section, name, value):
        if name == "lookup_table_orientation":
            self.__config_load_lookup_table_orientation()
        elif name == "auto_hide":
            self.__config_load_auto_hide()
        elif name == "use_custom_font" or name == "custom_font":
            self.__config_load_custom_font()

    def __config_reloaded_cb(self, bus):
        pass

    def __create_sys_menu(self):
        menu = gtk.Menu()
        item = gtk.ImageMenuItem(gtk.STOCK_PREFERENCES)
        item.connect("activate",
            self.__sys_menu_item_activate_cb, gtk.STOCK_PREFERENCES)
        menu.add(item)
        item = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
        item.connect("activate",
            self.__sys_menu_item_activate_cb, gtk.STOCK_ABOUT)
        menu.add(item)
        menu.add(gtk.SeparatorMenuItem())
        item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        item.connect("activate",
            self.__sys_menu_item_activate_cb, gtk.STOCK_QUIT)
        menu.add(item)

        menu.show_all()
        menu.set_take_focus(False)
        return menu

    def __create_im_menu(self):
        menu = gtk.Menu()
        factories = self.__bus.get_factories()

        if not factories:
            item = gtk.MenuItem(label = "no engine")
            item.set_sensitive(False)
            menu.add(item)
        else:
            tmp = {}
            for factory in factories:
                name, lang, icon, authors, credits = self.__bus.get_factory_info(factory)
                lang = ibus.get_language_name(lang)
                if not icon:
                    icon = "engine-default"
                if lang not in tmp:
                    tmp[lang] = []
                tmp[lang].append((name, lang, icon, authors, credits, factory))
            langs = tmp.keys()
            other = tmp.get(_("Other"), [])
            if _("Other") in tmp:
                langs.remove(_("Other"))
                langs.append(_("Other"))
            for lang in langs:
                if len(tmp[lang]) == 1:
                    name, lang, icon, authors, credits, factory = tmp[lang][0]
                    item = gtk.ImageMenuItem("%s - %s" % (lang, name))
                    size = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
                    item.set_image (_icon.IconWidget(icon, size[0]))
                    item.connect("activate", self.__im_menu_item_activate_cb, factory)
                    menu.add(item)
                else:
                    item = gtk.MenuItem(lang)
                    menu.add(item)
                    submenu = gtk.Menu()
                    item.set_submenu(submenu)
                    for name, __lang, icon, authors, credits, factory in tmp[lang]:
                        item = gtk.ImageMenuItem(name)
                        size = gtk.icon_size_lookup(gtk.ICON_SIZE_MENU)
                        item.set_image (_icon.IconWidget(icon, size[0]))
                        item.connect("activate", self.__im_menu_item_activate_cb, factory)
                        submenu.add(item)

        menu.show_all()
        menu.set_take_focus(False)
        return menu

    def __get_im_menu_cb(self, languagebar):
        menu = self.__create_im_menu()
        return menu

    def __status_icon_popup_menu_cb(self, status_icon, button, active_time):
        menu = self.__create_sys_menu()
        menu.popup(None, None,
                gtk.status_icon_position_menu,
                button,
                active_time,
                self.__status_icon)

    def __status_icon_activate_cb(self, status_icon):
        if not self.__focus_ic:
            return
        menu = self.__create_im_menu()
        menu.popup(None, None,
                gtk.status_icon_position_menu,
                0,
                gtk.get_current_event_time(),
                self.__status_icon)

    def __im_menu_item_activate_cb(self, item, factory):
        self.__bus.set_factory(factory)

    def __sys_menu_item_activate_cb(self, item, command):
        if command == gtk.STOCK_PREFERENCES:
            self.__start_setup()
        elif command == gtk.STOCK_ABOUT:
            about_dialog = gtk.AboutDialog()
            about_dialog.set_program_name("iBus")
            about_dialog.set_version(ibus.get_version())
            about_dialog.set_copyright(ibus.get_copyright())
            about_dialog.set_license(ibus.get_license())
            about_dialog.set_comments(_("IBus is an intelligent input bus for Linux/Unix."))
            about_dialog.set_website("http://code.google.com/p/ibus")
            about_dialog.set_authors(["Huang Peng <shawn.p.huang@gmail.com>"])
            about_dialog.set_documenters(["Huang Peng <shawn.p.huang@gmail.com>"])
            about_dialog.set_translator_credits(_("translator-credits"))
            about_dialog.set_logo_icon_name("ibus")
            about_dialog.run()
            about_dialog.destroy()
        elif command == gtk.STOCK_QUIT:
            self.__bus.kill()
        else:
            print >> sys.stderr, "Unknown command %s" % command
    
    def __sigchld_cb(self, sig, sf):
        pid, status = os.wait()
        if self.__setup_pid == pid:
            self.__setup_pid = 0

    def __start_setup(self):
        if self.__setup_pid != 0:
            pid, state = os.waitpid(self.__setup_pid, os.P_NOWAIT)
            if pid != self.__setup_pid:
                return
            self.__setup_pid = 0
        self.__setup_pid = os.spawnl(os.P_NOWAIT, self.__setup_cmd, "ibus-setup")

gobject.type_register(Panel, "IBusPanel")
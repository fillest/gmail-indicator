#coding: utf-8
import urllib2
import contextlib
import base64
import argparse
import traceback
import xml.etree.ElementTree as ET
import webbrowser
import logging
import threading
import time
import gtk #TODO proper importing
from gtk import gdk
import cairo
import gobject


gobject.threads_init()


logging.basicConfig(level = logging.INFO, format = "%(asctime)s %(funcName)s:%(lineno)d %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


#https://developers.google.com/google-apps/gmail/gmail_inbox_feed
GMAIL_FEED_URL = 'https://mail.google.com/mail/feed/atom/'


def parse_args ():
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--interval', default = 10, type = int, help = "Interval between checks (in seconds)")
	parser.add_argument('-ft', '--fetch-thread-timeout', default = 60 * 10, type = int)
	parser.add_argument('username')
	parser.add_argument('password')
	return parser.parse_args()

class FetchError (Exception):
	pass

class AuthError (Exception):
	pass

def raise_fetch_error ():
	log.warning("Exception while fetching feed:\n%s" % traceback.format_exc())
	raise FetchError()

def fetch_feed (user, password):
	#IMAP 'UNSEEN' returns strange number (bigger than expected -- maybe plain msg list, not chains?) so use the feed
	req = urllib2.Request(GMAIL_FEED_URL)
	req.add_header('Authorization', "Basic " + base64.encodestring("%s:%s" % (user, password)))
	try:
		with contextlib.closing(urllib2.urlopen(req)) as resp:
			return resp.read()
	except urllib2.HTTPError as e:
		if e.code == 401:
			raise AuthError()
		else:
			raise_fetch_error()
	except:
		raise_fetch_error()

def fetch_recent_unread_entries (user, password):
	data = fetch_feed(user, password)

	data = data.replace('xmlns', 'dummy')
	feed = ET.fromstring(data)
	
	total_unread_num = int(feed.find('fullcount').text)
	entries = []
	if total_unread_num:
		for e in feed.findall('entry'):
			entries.append((
				e.find('author/name').text,
				e.find('title').text,
				e.find('link').get('href'),
			))
	return total_unread_num, entries

def on_menu_entry_click (_widget, url):
	# print url
	threading.Thread(target = lambda: webbrowser.open(url)).start()

def show_menu (status_icon, button, activate_time, entries):
	menu = gtk.Menu()

	for name, title, link in entries:
		item = gtk.MenuItem(u"%s — %s" % (title, name))
		item.connect('activate', on_menu_entry_click, link)
		menu.append(item)

	if entries:
		menu.append(gtk.SeparatorMenuItem())
	quit = gtk.ImageMenuItem(stock_id = gtk.STOCK_QUIT)
	quit.connect('activate', lambda w: gtk.main_quit())
	menu.append(quit)

	menu.show_all()

	menu.popup(None, None, gtk.status_icon_position_menu, button, activate_time, status_icon)

	# for item in menu.get_children():
	# 	item.destroy()
	# menu.destroy()

def run ():
	args = parse_args()

	recent_unread_entries = []

	status_icon = gtk.StatusIcon()
	status_icon.set_from_stock(gtk.STOCK_REFRESH)  #https://developer.gnome.org/gtk3/stable/gtk3-Stock-Items.html
	status_icon.connect('popup-menu', show_menu, recent_unread_entries)
	# def test (m, _):
	# 	menu = gtk.Menu()
	# 	quit = gtk.MenuItem("Quit")
	# 	menu.append(quit)
	# 	quit.connect('activate', lambda w: gtk.main_quit())
	# 	menu.show_all()
	# 	menu.popup(None, None, gtk.status_icon_position_menu, 0, 0, status_icon)
	# status_icon.connect('activate', test, recent_unread_entries)
	# def t (status_icon, size, _):
	# 	print size
	# status_icon.connect('size-changed', t, recent_unread_entries)
	status_icon.set_tooltip("%s@gmail.com" % args.username)

	traySize = 24
	trayPixbuf = gdk.Pixbuf(gdk.COLORSPACE_RGB, True, 8, traySize, traySize)
	# trayPixbuf = trayPixbuf.add_alpha(True, 0xFF, 0xFF, 0xFF)
	# trayPixbuf.fill(0xffffffff)
	trayPixbuf.fill(0x00000000)

	pixmap = trayPixbuf.render_pixmap_and_mask(alpha_threshold = 127)[0]
	cr = pixmap.cairo_create()
	# cr.select_font_face("Georgia", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
	cr.set_operator(cairo.OPERATOR_SOURCE)
	cr.set_source_rgba(1, 1, 1, 1)
	font_size = 15
	cr.set_font_size(font_size)
	trayPixbuf.get_from_drawable(pixmap, pixmap.get_colormap(), 0, 0, 0, 0, traySize, traySize)
	trayPixbuf = trayPixbuf.add_alpha(True, 0x00, 0x00, 0x00)
	# trayPixbuf = trayPixbuf.add_alpha(True, 0xFF, 0xFF, 0xFF)
	# status_icon.set_from_pixbuf(trayPixbuf)
	# print status_icon.get_size()
	# print status_icon.get_geometry()

	def check_mail_loop ():
		try:
			result = {}
			result['total_num'] = None
			while True:
				# print "fetch start"
				result['failed'] = False
				def fetch ():
					try:
						result['total_num'], result['entries'] = fetch_recent_unread_entries(args.username, args.password)
					except FetchError:
						result['failed'] = True
					except AuthError:
						def show_auth_error ():
							md = gtk.MessageDialog(None, gtk.DIALOG_MODAL, gtk.MESSAGE_ERROR, gtk.BUTTONS_CLOSE,
								u"Gmail refused to authorize '%s'\nPlease check your credentials spelling" % args.username)
							md.run()
							md.destroy()
							gtk.main_quit()
						gobject.idle_add(show_auth_error)
						return
					# print "fetch done"
				#a workaround for stange occasional hanging
				#http://stackoverflow.com/questions/16772795/urllib2-urlopen-will-hang-forever-despite-of-timeout
				#another possible method but without windows support http://stackoverflow.com/questions/5565291/detecting-hangs-with-python-urllib2-urlopen/5565757#5565757
				thr = threading.Thread(target = fetch)
				# thr.daemon = True #TODO #is inherited?
				thr.start()
				thr.join(args.fetch_thread_timeout)
				if thr.isAlive():
					log.warning("fetch thread timeout")
					#TODO it leaks - thread is not killed

				if result['total_num'] is not None:
					def update_icon ():
						try:
							recent_unread_entries[:] = result['entries']

							cr.set_operator(cairo.OPERATOR_CLEAR)
							cr.paint()
							cr.set_operator(cairo.OPERATOR_SOURCE)
							cr.move_to(0, 16)
							if result['failed']:
								cr.set_font_size(12)
							else:
								cr.set_font_size(font_size)
							cr.show_text(str(result['total_num']) + ('?' if result['failed'] else ''))
							trayPixbuf.get_from_drawable(pixmap, pixmap.get_colormap(), 0, 0, 0, 0, traySize, traySize)
							p = trayPixbuf.add_alpha(True, 0x00, 0x00, 0x00)
							status_icon.set_from_pixbuf(p)
						except:
							#exception doesn't break gtk loop here
							gtk.main_quit()
							raise
					gobject.idle_add(update_icon)
					#TODO optionally show notification if got a new message

				time.sleep(args.interval)
		except:
			log.error("Unexpected exception in check_mail_loop:\n%s" % traceback.format_exc())
			gobject.idle_add(gtk.main_quit)
			#re-raise here will not cause trace to be printed 

	thr = threading.Thread(target = check_mail_loop)
	thr.daemon = True #TODO
	thr.start()

	gtk.main()


if __name__ == '__main__':
	run()

import urllib2
import contextlib
import base64
import argparse
import traceback
import xml.etree.ElementTree as ET
import webbrowser
import logging
import appindicator
import gtk


logging.basicConfig(level = logging.INFO, format = "%(asctime)s %(funcName)s:%(lineno)d %(levelname)s: %(message)s")
log = logging.getLogger(__name__)


#https://developers.google.com/google-apps/gmail/gmail_inbox_feed
GMAIL_FEED_URL = 'https://mail.google.com/mail/feed/atom/'


def parse_args ():
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--interval', type = int, default = 7, help = "Interval of checks in seconds")
	parser.add_argument('credentials', nargs = '+', help = "E.g. name1 passwd1 name2 passwd2")
	args = parser.parse_args()
	assert len(args.credentials) % 2 == 0
	return args

class FetchError (Exception):
	pass

def fetch_feed (user, password):
	#IMAP 'UNSEEN' return strange number (bigger than expected) so use the feed
	req = urllib2.Request(GMAIL_FEED_URL)
	req.add_header('Authorization', "Basic " + base64.encodestring("%s:%s" % (user, password)))
	try:
		with contextlib.closing(urllib2.urlopen(req)) as resp:
			return resp.read()
	except KeyboardInterrupt:
		raise
	except:
		log.warning("Exception during fetching feed:\n%s" % traceback.format_exc())
		raise FetchError()

def fetch_recent_unread_entries (user, password):
	data = fetch_feed(user, password)

	feed = ET.fromstring(data.replace('xmlns', 'dummy'))  #get rid of namespace bullshit boilerplate
	
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

def run ():
	args = parse_args()

	#http://conjurecode.com/create-indicator-applet-for-ubuntu-unity-with-python/
	#http://bazaar.launchpad.net/~indicator-sysmonitor-developers/indicator-sysmonitor/trunk/view/head:/indicator-sysmonitor
	menu = gtk.Menu()
	quit_item = gtk.ImageMenuItem(stock_id = gtk.STOCK_QUIT)
	quit_item.connect('activate', lambda _widget: gtk.main_quit())
	quit_item.show()
	menu.append(quit_item)

	ind = appindicator.Indicator("gmail-indicator-indicator", 'indicator-messages', appindicator.CATEGORY_APPLICATION_STATUS)
	ind.set_status(appindicator.STATUS_ACTIVE)
	ind.set_label("loading...")
	ind.set_menu(menu)

	sep = gtk.SeparatorMenuItem()
	sep.show()

	def check_mail (once):
		nums = []
		combined_entries = []
		try:
			for user, pwd in zip(*[iter(args.credentials)] * 2):
				total_num, entries = fetch_recent_unread_entries(user, pwd)

				nums.append(str(total_num))
				combined_entries += entries
		except FetchError:
			if not ind.get_label().endswith("?"):
				ind.set_label(ind.get_label() + "?")
			return not once
		except:
			gtk.main_quit()
			raise

		#TODO optionally show notification if got a new message

		ind.set_label(", ".join(nums))

		#TODO rebuild the menu only if feed has changed
		map(menu.remove, menu.get_children())

		def make_callback (url):
			return lambda _widget: webbrowser.open(url)
		for name, title, link in combined_entries:
			item = gtk.MenuItem(u"%s - %s" % (name, title))
			item.connect('activate', make_callback(link))
			item.show()
			menu.append(item)
		
		if combined_entries:
			menu.append(sep)
		menu.append(quit_item)
		
		return not once

	#check mail right away. delay is to avoid blocking icon rendering
	gtk.timeout_add(300, check_mail, True)
	
	gtk.timeout_add(args.interval * 1000, check_mail, False)

	try:
		gtk.main()
	except KeyboardInterrupt:
		pass


if __name__ == '__main__':
	run()
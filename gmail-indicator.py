import urllib2
import contextlib
import re
import base64
import argparse
import traceback
import logging
import appindicator
import gtk


logging.basicConfig(level = logging.INFO, format = '%(asctime)s %(funcName)s:%(lineno)d %(levelname)s: %(message)s')
log = logging.getLogger(__name__)

#https://developers.google.com/google-apps/gmail/gmail_inbox_feed
GMAIL_FEED_URL = "https://mail.google.com/mail/feed/atom/"

def fetch_unread_num (user, password):
	#IMAP 'UNSEEN' return a strange number (bigger than expected) so use the feed
	req = urllib2.Request(GMAIL_FEED_URL)
	req.add_header('Authorization', "Basic " + base64.encodestring("%s:%s" % (user, password)))
	with contextlib.closing(urllib2.urlopen(req)) as resp:
		data = resp.read()
	return int(re.search('<fullcount>(\d+)</fullcount>', data).group(1))

def parse_args ():
	parser = argparse.ArgumentParser()
	parser.add_argument('-i', '--interval', type = int, default = 7, help = "Interval of checks in seconds")
	parser.add_argument('credentials', nargs = '+', help = "E.g. name1 passwd1 name2 passwd2")
	args = parser.parse_args()
	assert len(args.credentials) % 2 == 0
	return args

def run ():
	args = parse_args()

	#http://conjurecode.com/create-indicator-applet-for-ubuntu-unity-with-python/
	#http://bazaar.launchpad.net/~indicator-sysmonitor-developers/indicator-sysmonitor/trunk/view/head:/indicator-sysmonitor
	ind = appindicator.Indicator("gmail-indicator-indicator", 'indicator-messages', appindicator.CATEGORY_APPLICATION_STATUS)
	# ind.set_attention_icon('new-messages-red')
	ind.set_status(appindicator.STATUS_ACTIVE)
	ind.set_label("loading...")

	menu = gtk.Menu()
	quit_item = gtk.ImageMenuItem(stock_id = gtk.STOCK_QUIT)
	# menu.add(gtk.SeparatorMenuItem())
	quit_item.connect('activate', lambda _widget: gtk.main_quit())
	quit_item.show()
	menu.append(quit_item)
	ind.set_menu(menu)

	def check_mail (once):
		nums = []
		for user, pwd in zip(*[iter(args.credentials)] * 2):
			try:
				num = fetch_unread_num(user, pwd)
			except:
				log.error("Exception during fetching:\n%s" % traceback.format_exc())
				if not ind.get_label().endswith('?'):
					ind.set_label(ind.get_label() + "?")
				return not once
			else:
				nums.append(str(num))

		ind.set_label(", ".join(nums))
		
		return not once

	gtk.timeout_add(300, check_mail, True)
	gtk.timeout_add(args.interval * 1000, check_mail, False)

	try:
		gtk.main()
	except KeyboardInterrupt:
		pass


if __name__ == "__main__":
	run()
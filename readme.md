# Gmail Indicator

* A desktop application that shows Gmail inbox unread message number in the notification area.
* When new email arrives, the indicator gets highlighted.
* Click the indicator to show a menu with latest message titles. Click a message to open it in Gmail in your browser.
* Run multiple program instances for multiple accounts.

Example screenshot:
![screenshot](http://s.fillest.ru/published/gmail-indicator.png)

Tested currently only on Linux (Ubuntu).

Written in Python with no external dependencies beside GTK/Cairo.


## Usage
The program gets password from the config file (`~/.gmail_indicator.ini` by default). Create and fill this file with your email(s) and password(s):
```ini
[youremail@gmail.com]
password = yourpassword

[your-other-email@gmail.com]
password = your-other-password
```

Then run:
```bash
python gmail-indicator.py youremail@gmail.com
```

Run more instances for your other accounts passing email as argument.

You may also add it to your startup applications:
```bash
python /home/youruser/path/to/gmail-indicator.py youremail@gmail.com
```


## Feedback
Please submit any bugs or feedback to [the issue tracker](https://github.com/fillest/gmail-indicator/issues).

Contributions are welcome.


## License
See license.txt ([The MIT License](http://www.opensource.org/licenses/mit-license.php))

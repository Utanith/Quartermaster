import sqlite3
from datetime import date
import sopel.module as module
from sopel.config.types import StaticSection, ValidatedAttribute, FilenameAttribute

class QuoteSection(StaticSection):
	dbname = FilenameAttribute('dbname', default="./quotes.db")


@module.commands('qstats')
def stats(bot, trigger):
	"""Shows the number of quotes in the quote database."""
	db = sqlite3.connect(bot.config.quote.dbname)
	c = db.cursor()

	res = c.execute('''SELECT COUNT(*) FROM quotes;''')
	count = res.fetchone()[0]
	bot.say("I have recorded {} quotes.".format(count))
	
@module.commands('delete')
@module.require_admin()
def remove(bot, trigger):
	db = sqlite3.connect(bot.config.quote.dbname)
	c = db.cursor()
	
	number = trigger.group(3)
	c.execute('''SELECT * FROM quotes WHERE ROWID = ?''', (number,))
	row = c.fetchone()
	if(row is not None):
		c.execute('''INSERT INTO deleted VALUES (?, ?)''', (row[0], row[1]))
		c.execute('''DELETE FROM quotes WHERE ROWID = ?''', (number,))
	db.commit()
	bot.say('Deleted quote {} ({})'.format(number, row[1]))
		

@module.commands('quote')
@module.example('.quote Dragon')
@module.example('.quote 17')
def quote(bot, trigger):
	"""Retrieve a random quote, a specific quote, or a quote for a specific user if specified"""
	db = sqlite3.connect(bot.config.quote.dbname)
	c = db.cursor()
	
	nick = trigger.group(3)
	if int(nick):
		c.execute('''SELECT ROWID,* FROM quotes WHERE ROWID = ?''', (nick,))
	elif nick:
		nick = nick.strip()
		c.execute('''SELECT ROWID,* FROM quotes WHERE nick = ? ORDER BY RANDOM() LIMIT 1''', (nick,))
	else:
		c.execute('''SELECT ROWID,* FROM quotes ORDER BY RANDOM() LIMIT 1''')

	row = c.fetchone()
	if(row == None):
		bot.say("I have no quotes for {} recorded.".format(nick))
		return

	db.close()
	bot.say("[{}] {}".format(row[0], row[2]))


@module.commands('record')
@module.example('.record Dragon')
def record(bot, trigger):
	"""Record the last thing a user said in the quote database"""
	db = sqlite3.connect(bot.config.quote.dbname)
	c = db.cursor()

	raw = trigger.group(2)

	nick = trigger.nick
	if(raw):
		nick = raw.strip()

	quote = bot.db.get_nick_value(nick, 'lastsaid')
	if quote is None:
		bot.say("I don't have a quote for " + nick + " recorded.")
		return

	msg = """"{}" ~{}, {}""".format(quote[0], nick, date.today().year)

	if len(msg) > 400:
		bot.say("Sorry, that just isn't catchy enough.")
		return

	c.execute('''INSERT INTO quotes VALUES (?, ?)''', (nick, msg))
	qid = c.lastrowid
	db.commit()
	db.close()
	bot.db.set_nick_value(nick, 'lastsaid', None)
	bot.say("Quote [{}] recorded!".format(qid))


@module.rule('(.+)')
@module.require_chanmsg()
def memorize(bot, trigger):
	if(trigger.groups(0)[0] != "."):
		bot.db.set_nick_value(trigger.nick, 'lastsaid', trigger.groups(0))

def setup(bot):
	bot.config.define_section('quote', QuoteSection)
	db = sqlite3.connect(bot.config.quote.dbname)
	c = db.cursor()
	c.execute('''CREATE TABLE if not exists quotes (nick text, quote text)''')
	c.execute('''CREATE TABLE IF NOT EXISTS deleted (nick text, quote text)''')
	db.commit()
	db.close()

def configure(config):
	config.define_section('quote', QuoteSection, validate = False)
	config.quote.configure_setting(
		'dbname',
		'Enter a filename for the quote database.',
	)

#!/usr/bin/python3
from datetime import date
import sqlite3
from sopel.config.types import (
		StaticSection, FilenameAttribute, ValidatedAttribute
	)
import sopel.module as module
import re

def setup(bot):
    bot.db.execute("CREATE TABLE IF NOT EXISTS karma_values (thing text unique, karma int)")
    bot.db.execute("CREATE TABLE IF NOT EXISTS karma_log (thing int, reason text)")

@module.rule('(.+)(\+\+|\-\-)( .+)?')
def add_karma(bot, trigger):
    db = bot.db

    print(trigger.groups())

    args = len(trigger.groups())
    msg = thing = sign = reason = None
    if args == 3:
        thing, sign, reason = trigger.groups()
    else:
        bot.reply("Invalid syntax")
        return

    print(msg)

    sign = sign[-2:]

    if thing is None:
        return
    
    thing = thing.lower()
    if thing == trigger.nick.lower():
        return

    val = 0
    tid = None

    if sign == "++":
        res = db.execute("SELECT ROWID, karma FROM karma_values WHERE thing = ?", (thing,))
        res = res.fetchall()
        if len(res) == 1:
            tid = res[0][0]
            val = res[0][1]
            val += 1
            db.execute("UPDATE karma_values SET karma = ? WHERE thing = ?", (val, thing))
        else:
            res = db.execute("INSERT INTO karma_values VALUES (?, ?)", (thing, 1))
            tid = res.lastrowid
            val = 1
    else:
        res = db.execute("SELECT ROWID, karma FROM karma_values WHERE thing = ?", (thing,))
        res = res.fetchall()
        if len(res) == 1:
            tid = res[0][0]
            val = res[0][1]
            val -= 1
            db.execute("UPDATE karma_values SET karma = ? WHERE thing = ?", (val, thing))
        else:
            res = db.execute("INSERT INTO karma_values VALUES (?, ?)", (thing, -1))
            tid = res.lastrowid
            val = -1

    if val:
        bot.say("[KARMA] {} now has {} karma.".format(thing, val))

    if tid:
        if reason:
            reason = "<{}>: {}{} {}".format(trigger.nick, thing, sign, reason.strip())
        else:
            reason = "<{}>: {}{}".format(trigger.nick, thing, sign)
        db.execute("INSERT INTO karma_log VALUES (?, ?)", (tid, reason))

@module.commands('klog')
@module.example('.klog Dragon')
def klog(bot, trigger):
    args = trigger.group(0).split(" ")
    if args[0] != ".klog":
        return

    thing = args[1]
    res = bot.db.execute("SELECT ROWID, karma FROM karma_values WHERE thing = ?", (thing,))
    res = res.fetchall()
    if len(res) == 1:
        tid = res[0][0]
        karma = res[0][1]
    else:
        bot.reply("No karma for {}.".format(thing))

    bot.say("[KARMA] {} has {} karma.".format(thing, karma))

    limit = 3
    if len(args) == 3:
        try:
            limit = int(args[2])
        except:
            limit = 3

    res = bot.db.execute("SELECT reason FROM karma_log WHERE thing = ? ORDER BY ROWID DESC LIMIT ?", (tid,limit))
    for i in res.fetchall():
        bot.say("[KARMA] {}".format(i[0]))

@module.commands('top')
@module.example('.top Gold')
def showTop(bot, trigger):
	"""Lists the top users for a currency"""
	coins = CoinPouch()

	res = coins.getLeaders(trigger.group(3))
	res = sorted(res, key=lambda u: u[2])
	for u, p, v in reversed(res):
		bot.say(coins.getUserName(u) + " has " + str(v) + " " + trigger.group(3))


@module.commands("points")
@module.example(".points Gold")
def showUser(bot, trigger):
	"""Shows all of a user's currencies"""
	coins = CoinPouch()

	user = coins.getAllPoints(trigger.group(3))
	for x in user:
		bot.say(x[0] + " has " + str(x[2]) + " " + x[1])


@module.commands("register")
def register(bot, trigger):
	"""Registers the current user, allowing them to accumulate currency"""
	coins = CoinPouch()

	if coins.getUserId(trigger.nick):
		bot.say("You're already registered!")
		return

	coins.addUser(trigger.nick)
	bot.say(trigger.nick + " can now receive points.")


@module.commands("mint")
@module.example(".mint Gold")
def mint(bot, trigger):
	"""Names your personal currency."""
	coins = CoinPouch()
	if not coins.getUserId(trigger.nick):
		bot.say("You must register (.register) first!")
		return

	if coins.getPointId(trigger.group(3)):
		bot.say("That currency already exists!")
		return

	old = coins.getUserCoin(trigger.nick)
	if old:
		coins.namePoints(old, trigger.group(3))
	else:
		coins.addPoints(trigger.group(3), trigger.nick)
		
	bot.say("Your currency is now called \"" + trigger.group(3) + "\".")


@module.commands("give")
@module.example(".give Dragon 20")
@module.example(".give arctem -10")
def mod(bot, trigger):
	"""Add or subtract your currency from a user's bank."""
	coins = CoinPouch()
	mod = 0
	try:
		mod = int(trigger.group(4))
	except:
		bot.say("Whole numbers only, please.")
		return

	if mod > 1000000 or mod < -1000000:
		bot.say("No transactions over 1000000, please.")
		return
	user = trigger.group(3)

	if not coins.getUserId(user):
		bot.say("No such user " + user)
		return

	coin = coins.getUserCoin(trigger.nick)
	if not coin:
		bot.say("You need to start a currency first. .mint <currency>")
		return

	points = coins.getPoints(user, coin)
	bot.say("Adding {mod} {coin} to {user}'s bank (Which had {prev} {coin}.)"
		.format(mod=mod, coin=coin, user=user, prev=points))
	if not coins.modPoints(trigger.nick, coin, user, mod):
		bot.say("You can only give out ten " + coin + " per day.")

	points = coins.getPoints(user, coin)
	bot.say(user + " now has " + str(points) + " " + coin)


class CoinPouch:
	db = None

	def __init__(self):
		self.getDb()
		c = self.db.cursor()
		c.execute('''create table if not exists points (
				name text UNIQUE,
				user text
				);''')
		c.execute('''create table if not exists users (name text UNIQUE);''')
		c.execute('''create table if not exists bank (
				user integer,
				points integer,
				score integer,
				unique(points, user)
				);''')
		c.execute('''create table if not exists log (user integer, count integer, time text);''')
		self.db.commit()


	def addUser(self, name):
		c = self.db.cursor()
		c.execute('''INSERT INTO users VALUES (?);''', (name,))
		self.db.commit()


	def addPoints(self, name, user):
		c = self.db.cursor()
		c.execute('''INSERT INTO points VALUES (?, ?);''', (name,user))
		self.db.commit()

	def namePoints(self, old, new):
		c = self.db.cursor()
		c.execute('''UPDATE points SET name = ? WHERE name = ?''', (new, old))
		self.db.commit()

	def getUserId(self, name):
		c = self.db.cursor()
		c.execute('''SELECT ROWID FROM users WHERE name = ?;''', (name,))
		row = c.fetchone()
		if row:
			return row[0]
		else:
			return None

	def getUserCoin(self, name):
		c = self.db.cursor()
		c.execute('''SELECT * FROM points WHERE user = ?''', (name,))
		row = c.fetchone()
		if row:
			return row[0]
		else:
			return None

	def getUserName(self, uid):
		c = self.db.cursor()
		c.execute('''SELECT name FROM users WHERE ROWID = ?;''', (uid,))
		return c.fetchone()[0]


	def getPointName(self, pid):
		c = self.db.cursor()
		c.execute('''SELECT name FROM points WHERE ROWID = ?''', (pid,))
		return c.fetchone()[0]


	def getPointId(self, name):
		c = self.db.cursor()
		c.execute('''SELECT ROWID FROM points WHERE name = ?;''', (name,))
		row = c.fetchone()
		if row:
			return row[0]
		else:
			return None


	def getAllPoints(self, name):
		c = self.db.cursor()
		user = self.getUserId(name)

		c.execute('''SELECT * FROM bank WHERE user = ?''', (user,))
		res = c.fetchall()

		out = []
		for u, p, s in res:
			out.append((name, self.getPointName(p), s))

		return out


	def getPoints(self, name, points):
		c = self.db.cursor()
		user = self.getUserId(name)
		pid = self.getPointId(points)

		c.execute('''SELECT * FROM bank WHERE user = ? AND points = ?;''', (user, pid))
		row = c.fetchone()
		if row is None:
			return None
		else:
			return row[2]


	def getLeaders(self, points):
		c = self.db.cursor()
		pid = self.getPointId(points)
		c.execute('''SELECT * FROM bank WHERE points = ? ORDER BY score DESC LIMIT 5''', (pid,))
		res = c.fetchall()
		return res


	def modPoints(self, sender, points, name, mod):
		c = self.db.cursor()
		user = self.getUserId(name)
		pid = self.getPointId(points)
		today = date.today()

		pval = self.getPoints(name, points)

		c.execute('''SELECT count FROM log WHERE user = ? AND time = ?;''', (self.getUserId(sender), today))
		res = c.fetchall()

		total = 0
		for row in res:
			total += abs(int(row[0]))

		if total >= 10 or (total + mod) > 10:
			return False

		if pval is not None:
			c.execute('''UPDATE bank SET score = ? WHERE user = ? AND points = ?;''', (pval + int(mod), user, pid))
		else:
			c.execute('''INSERT INTO bank VALUES (?, ?, ?);''', (user, pid, int(mod)))

		
		c.execute('''INSERT INTO log VALUES (?, ?, ?);''', (self.getUserId(sender), int(mod), today))
		self.db.commit()
		return True


	def getDb(self):
		self.db = sqlite3.connect("./points.db")


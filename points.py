#!/usr/bin/python3
from datetime import date
import sqlite3
from sopel.config.types import (
        StaticSection, FilenameAttribute, ValidatedAttribute
    )
import sopel.module as module
import re
import time


def setup(bot):
    bot.db.execute("CREATE TABLE IF NOT EXISTS karma_values (thing text unique, karma int)")
    bot.db.execute("CREATE TABLE IF NOT EXISTS karma_log (thing int, reason text)")
    bot.db.execute("CREATE TABLE IF NOT EXISTS karma_aliases (thing text, alias text unique)")


def _get_thing_id(db, thing):
    thing = _is_alias(db, thing)
    res = db.execute("SELECT ROWID from karma_values WHERE thing = ?", (thing,))
    res = res.fetchall()
    if len(res) == 1:
        return res[0][0]
    return None


def _is_alias(db, thing):
    res = db.execute("SELECT thing FROM karma_aliases WHERE alias = ?", (thing,))
    res = res.fetchall()
    if len(res) == 1:
        return res[0][0]
    return thing


def _get_karma(db, thing):
    karma = 0
    thing = _is_alias(db, thing)
    res = db.execute("SELECT ROWID, karma FROM karma_values WHERE thing = ?", (thing,))
    res = res.fetchall()
    if len(res) == 1:
        karma = res[0][1]
        return karma
    return 0

def _add_karma(thing, db, sign):
    if thing is None:
        return

    thing = thing.lower()
    if not _get_thing_id(db, thing):
        db.execute("INSERT INTO karma_values values (?, 0)", (thing,))

    val = _get_karma(db, thing)

    try:
        if sign == 1:
            val += 1
            db.execute("UPDATE karma_values SET karma = ? WHERE thing = ?", (val, thing))
        elif sign == -1:
            val -= 1
            db.execute("UPDATE karma_values SET karma = ? WHERE thing = ?", (val, thing))
    except:
        return None
    return val


def _is_on_cooldown(db, sender):
    ctime = db.get_nick_value(sender, 'karma_time')
    if ctime is not None:
        if ctime + 60 > time.time():
            return True
    return False


def _karma_log(db, thing, sender, sign, reason):
    tid = _get_thing_id(db, thing)

    if tid:
        if reason:
            reason = "<{}>: {}{} {}".format(sender, thing, sign, reason.strip())
        else:
            reason = "<{}>: {}{}".format(sender, thing, sign)
        db.execute("INSERT INTO karma_log VALUES (?, ?)", (tid, reason))

    db.set_nick_value(sender, "karma_time", time.time())


@module.rule('^(\-\-|\+\+)( .{1,75})?$')
def repeat_karma(bot, trigger):
    db = bot.db

    if 'lastkarma_' + trigger.sender in bot.memory:
        thing = bot.memory['lastkarma_' + trigger.sender]
        if _is_on_cooldown(db, trigger.nick):
            bot.reply("You can only do karma actions once every ten minutes.")
            return

        # Deny giving karma to self
        if thing == trigger.nick.lower():
            bot.reply("No.", trigger.sender, trigger.nick, notice=True)
            return

        # Further, deny the "namespace" of self
        if re.match("{}\_.*".format(trigger.nick.lower()), thing):
            bot.reply("No.", trigger.sender, trigger.nick, notice=True)
            return

        sign = trigger.group(1)

        if sign:
            val = _add_karma(thing, db, 1 if sign is '++' else -1)
            if val is not None:
                bot.say("[KARMA] {} now has {} karma.".format(thing, val))
                if trigger.group(2):
                    _karma_log(db, thing, trigger.nick, sign, trigger.group(2))
                else:
                    _karma_log(db, thing, trigger.nick, sign, None)


@module.rule('(.{3,15})(?:: )?(\+\+|\-\-)( .{1,75})?')
def add_karma(bot, trigger):
    db = bot.db

    sender = trigger.nick

    if _is_on_cooldown(db, sender):
        bot.reply("You can only do karma actions once every ten minutes.", trigger.sender, sender, notice=True)
        return

    args = len(trigger.groups())
    thing = sign = reason = None
    if args == 3:
        thing, sign, reason = trigger.groups()
    else:
        bot.reply("Invalid syntax", trigger.sender, sender, notice=True)
        return

    sign = sign[-2:]

    if thing is None:
        return

    thing = thing.lower()
    if thing == sender.lower():
        bot.reply("No.", trigger.sender, sender, notice=True)
        return

    # Further, deny the "namespace" of self
    if re.match("{}\_.*".format(trigger.nick.lower()), thing):
        bot.reply("No.", trigger.sender, sender, notice=True)
        return

    newsign = 1 if sign == "++" else -1
    val = _add_karma(thing, db, newsign)

    if val is not None:
        bot.say("[KARMA] {} now has {} karma.".format(thing, val))
        _karma_log(db, thing, sender, sign, reason)
    else:
        bot.reply("There was a problem.", trigger.sender, sender, notice=True)
        return

    bot.memory['lastkarma_' + trigger.sender] = thing

@module.commands('ktop')
@module.example('.ktop')
def ktop(bot, trigger):
    args = trigger.group(0).split(" ")

    limit = 5
    if len(args) == 2:
        limit = int(args[1])

    res = bot.db.execute("SELECT thing, karma FROM karma_values ORDER BY karma DESC LIMIT ?", (limit,))
    res = res.fetchall()
    rank = 1
    for thing in res:
        bot.say("[KARMA] #{} - {} has {} karma".format(rank, thing[0], thing[1]))
        rank += 1

@module.commands('klog')
@module.example('.klog Dragon')
def klog(bot, trigger):
    args = trigger.group(0).split(" ", 2)
    if args[0] != ".klog":
        return

    limit = 3
    thing = args[1].lower()
    try:
        limit = int(thing)
        thing = " ".join(args[2:])
    except:
        limit = 3
        thing = " ".join(args[1:])

    thing = _is_alias(bot.db, thing)

    karma = 0
    res = bot.db.execute("SELECT ROWID, karma FROM karma_values WHERE thing = ?", (thing,))
    res = res.fetchall()
    if len(res) == 1:
        tid = res[0][0]
        karma = res[0][1]
    else:
        bot.reply("No karma for {}.".format(thing))
        return

    bot.say("[KARMA] {} has {} karma.".format(thing, karma))

    res = bot.db.execute("SELECT reason FROM karma_log WHERE thing = ? ORDER BY ROWID DESC LIMIT ?", (tid, limit))
    for i in res.fetchall():
        bot.say("[KARMA] {}".format(i[0]))


@module.commands('kalias')
@module.example('.kalias Dragon Utanith')
@module.require_admin()
def kalias(bot, trigger):
    """
    .kalias <target> <alias>
    """
    thing = trigger.group(3)
    alias = trigger.group(4)
    thing = thing.lower()
    alias = alias.lower()
    res = bot.db.execute("SELECT ROWID,karma FROM karma_values WHERE thing = ?", (thing,))
    res = res.fetchall()
    if len(res) == 1:
        tid = res[0][0]
        val = res[0][1]
        res = bot.db.execute("SELECT * FROM karma_aliases WHERE alias = ?", (alias,))
        res = res.fetchall()
        if len(res) == 1:
            bot.reply("Alias already exists (It could refer to a different thing!)")
            return
        else:
            bot.db.execute("INSERT INTO karma_aliases VALUES (?, ?)", (thing, alias))
            res = bot.db.execute("SELECT karma, ROWID FROM karma_values WHERE thing = ?", (alias,))
            res = res.fetchall()
            if len(res) == 1:
                aval = res[0][0]
                oldid = res[0][1]
                newval = aval + val
                bot.db.execute("UPDATE karma_values SET karma = ? WHERE thing = ?", (newval, thing))
                bot.db.execute("UPDATE karma_log SET thing = ? WHERE thing = ?", (tid, oldid))
                bot.db.execute("DELETE FROM karma_values WHERE thing = ?", (alias,))
            bot.reply("Done.")
    else:
        bot.reply("Target for alias does not exist.")

@module.commands('kadmin')
@module.require_admin()
def kadmin(bot, trigger):
    subc = trigger.group(3).lower()

    if subc == "modify":
        thing = _is_alias(bot.db, trigger.group(4))
        val = int(trigger.group(5))
        oldval = _get_karma(bot.db, thing)
        if _get_thing_id(bot.db, thing):
            bot.db.execute("UPDATE karma_values SET karma = ? WHERE thing = ?", (val, thing))
        else:
            bot.db.execute("INSERT INTO karma_values VALUES (?, ?)", (thing, val))
        newval = _get_karma(bot.db, thing)
        sign = None
        diff = 0
        if oldval - newval >= 0:
            sign = "-"
            diff = oldval - newval
        else:
            sign = "+"
            diff = newval - oldval

        _karma_log(bot.db, thing, trigger.nick, sign, "ADMIN {}{}".format(sign, diff))
        bot.reply("{} now has {} karma.".format(thing, newval), trigger.sender, trigger.nick, notice=True)

    if subc == "list":
        res = bot.db.execute("SELECT thing, karma FROM karma_values")
        res = res.fetchall()
        for i in res:
            msg = "{}: {} karma".format(i[0], i[1])
            bot.reply(msg, trigger.sender, trigger.nick, notice=True)


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


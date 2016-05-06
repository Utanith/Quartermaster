#!/usr/bin/python3
from datetime import date
import sqlite3
from sopel.config.types import (
		StaticSection, FilenameAttribute, ValidatedAttribute
	)
import sopel.module as module

game = None

#@module.commands('take')
#@module.example('')
#def take(bot, trigger):
#    pass
#
#@module.commands('drop')
#def drop(bot, trigger):
#    pass
#
#@module.commands('wear')
#def wear(bot, trigger):
#    pass
#
#@module.commands('use')
#def use(bot, trigger):
#    pass

@module.commands('look')
def look(bot, trigger):
    uid = registerPlayer(bot.db, trigger.nick)
    obj = trigger.group(2)
    id = getID(bot.db, obj)

    if obj.lower() in ['here', 'room', '']:
        id = (-1, 'rom')
        roomDesc = getDesc(bot.db, id)
        if roomDesc is "":
            bot.notice("There's nothing here.", trigger.nick)
        bot.notice(roomDesc, trigger.nick)
        return

    bot.notice("{}: {}".format(obj, getDesc(bot.db, id)), trigger.nick)

@module.commands('describe')
def desc(bot, trigger):
    """Sets the description for an object"""
    obj, desc = trigger.group(2).split(" ", 1)
    uid = registerPlayer(bot.db, trigger.nick)
    id = getID(bot.db, obj)
    if id is -1:
        bot.notice("No such object {}.".format(obj), trigger.nick)
        return

    if id[1] is "plr":
        bot.notice("You can't describe other players!", trigger.nick)

    owner = getOwn(bot.db, id)

    if owner is not uid:
        bot.notice("You don't own that!", trigger.nick)
        return

    res = bot.db.execute("UPDATE rp_items SET desc = ? WHERE id = ?", (desc, id[0]))
    bot.notice("Updated the description of {}".format(obj), trigger.nick)

@module.commands('descself')
def descself(bot, trigger):
    """Sets the player's description"""
    uid = registerPlayer(bot.db, trigger.nick)
    desc = trigger.group(0).split(' ', 1)[1]

    bot.db.execute("UPDATE rp_players SET desc = ? WHERE id = ?", (desc, uid))
    bot.notice("Updated your description.", trigger.nick)

@module.commands('create')
def create(bot, trigger):
    obj = trigger.group(2).split(" ", 1)[1] 
    id = getID(bot.db, obj)

    if id is not -1:
        bot.notice("An object with that name already exists.", trigger.nick)
        return

    uid = registerPlayer(bot.db, trigger.nick)
    loc = "{}'s inventory".format(trigger.nick)

    bot.db.execute("BEGIN TRANSACTION")
    res = bot.db.execute("INSERT INTO rp_items(uid, name, desc, location) VALUES(?, ?, ?, ?)", (uid, obj, "", loc))
    if res.rowcount != 1:
        bot.db.execute("ROLLBACK")
        bot.notice("Sorry, there was a problem creating your item!", trigger.nick)

    res = bot.db.execute("INSERT INTO rp_inventory(uid, iid) VALUES(?, ?)", (uid, res.lastrowid))
    if res.rowcount != 1:
        bot.db.execute("ROLLBACK")
        bot.db.notice("Sorry, there was a problem creating your item!", trigger.nick)

    bot.db.execute("COMMIT")

    bot.notice("Created {}.".format(obj), trigger.nick)

@module.commands('drop')
def drop(bot, trigger):
    obj = trigger.group(2)
    iid = getID(bot.db, obj)
    uid = registerPlayer(bot.db, trigger.nick)

    if iid is -1:
        bot.notice("No such item.", trigger.nick)

    if iid[1] is 'plr':
        bot.notice("No such item.", trigger.nick)

    res = bot.db.execute("UPDATE rp_inventory SET uid = -1 WHERE uid = ? AND iid = ?", (uid, iid[0]))
    if res.rowcount is 0:
        bot.notice("You're not carrying that.", trigger.nick)

    bot.notice("{} drops {}.".format(trigger.nick, obj))


@module.commands('take')
def take(bot, trigger):
    obj = trigger.group(2)
    iid = getID(bot.db, obj)
    uid = registerPlayer(bot.db, trigger.nick)

    if iid is -1:
        bot.notice("No such item.", trigger.nick)

    if iid[0] is 'plr':
        bot.notice("No such item.", trigger.nick)

    res = bot.db.execute("UPDATE rp_inventory SET uid = ? WHERE uid = -1 AND iid = ?", (uid, iid[0]))
    if res.rowcount is 0:
        bot.notice("You can't pick that up.", trigger.nick)
    else:
        bot.notice("{} picked up {}.".format(trigger.nick, obj))

@module.commands(['inventory', 'i'])
def inven(bot, trigger):
    uid = registerPlayer(bot.db, trigger.nick)

    res = bot.db.execute('SELECT iid FROM rp_inventory WHERE uid = ?', (uid,))

    items = []
    for item in res:
        res = bot.db("SELECT name FROM rp_items WHERE id = ?", (item[0],))
        res = res.fetchone()
        if res:
            items.append(res[0])

    bot.notice("You are carrying: {}".format(", ".join(items)), trigger.nick)

def registerPlayer(db, player):
    uid = getID(db, player)
    if uid is not -1:
        return uid[0]

    res = db.execute("INSERT INTO rp_players(name, desc) VALUES(?, '')", (player,))
    return res.lastrowid


def getID(db, obj):
    t = "plr"
    res = db.execute("SELECT id FROM rp_players WHERE name = ?", (obj,)).fetchone()
    if res is None:
        t = "itm"
        res = db.execute("SELECT id FROM rp_items WHERE name = ?", (obj,)).fetchone()
        if res is None:
            return -1

    return (res[0], t)


def getOwn(db, id):
    res = db.execute("SELECT uid FROM rp_items WHERE id = ?", (id[0],)).fetchone()
    if res is None:
        return -1
    return res[0]


def getDesc(db, id):
    if id is -1:
        return "No such object."

    out = ""

    if id[1] == 'plr':
        out = db.execute("SELECT desc FROM rp_players WHERE id = ?", (id[0],)).fetchone()[0]
        print(out)
    elif id[1] == 'itm':
        out = db.execute("SELECT desc FROM rp_items WHERE id = ?", (id[0],)).fetchone()[0]
    elif id[1] == 'rom':
        res = db.execute("SELECT iid FROM rp_inventory WHERE uid = -1")
        if res is None:
            return "There's nothing here."
        items = []
        for item in res:
            name = db.execute("SELECT name FROM rp_items WHERE id = ?", (item[0],))
            if name is not None:
                name = name.fetchone()
                items.append(name[0])
        return "You see in the room: {}".format(", ".join(items))

    return out


def setup(bot):
    bot.db.execute("CREATE TABLE IF NOT EXISTS rp_players(id integer primary key autoincrement, name text unique, desc text);")
    bot.db.execute("CREATE TABLE IF NOT EXISTS rp_items(id integer primary key autoincrement, uid int, name text unique, desc text, location text);")
    bot.db.execute("CREATE TABLE IF NOT EXISTS rp_inventory(id integer primary key autoincrement, uid int, iid int)")

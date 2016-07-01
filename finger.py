import sopel.module as module
import re
import hmac
from datetime import datetime


def _dataScript(s, db, stack=None):
    data = s
    if data is None:
        return ""

    if stack:
        counts = {}
        for itm in stack:
            ident = "#{}#{}".format(itm[0], itm[1])
            if ident in counts:
                return ""
            else:
                counts[ident] = 1

    dt = datetime.now()

    if '$time' in data:
        data = data.replace('$time', dt.strftime("%H:%M:%S"))

    if '$date' in data:
        data = data.replace('$date', dt.strftime("%d/%m/%Y"))

    sub = re.findall("\{([\w\s\d]+)\:(!?[\w\s\d]{0,12})\}", data)
    for match in sub:
        linkU = match[0]
        linkK = match[1].lower()
        linkD = db.get_nick_value(linkU, "pks_" + linkK)
        if linkD is not None:
            if stack:
                stack.append((linkU, linkK))
                print(stack)
                linkD = _dataScript(linkD, db, stack)
            else:
                linkD = _dataScript(linkD, db, [(linkU, linkK)])
            link = "{}:{}".format("{" + linkU, match[1] + "}")
            data = re.sub(link, linkD, data)

    return data


@module.commands('finger')
def finger(bot, trigger):
    """`.finger [nick] [key]`- Lists your keys. With [nick] specified, lists that nick's keys. With [nick] and [key] specified, displays [nick]'s [key]."""
    user = trigger.nick
    key = None
    if trigger.group(2):
        if ' ' in trigger.group(2):
            user, key = trigger.group(2).split(" ", 1)
        else:
            user = trigger.group(2)

    if key and not re.match("[\w\s\d]{0,12}", key):
        bot.notice("{}: Sorry, keys may only contain alphanumerics and are limited to 12 characters.".format(trigger.nick), trigger.nick)
        return

    data = ""

    keystring = bot.db.get_nick_value(user, "pkskeys")
    if key is None and keystring is not None:
        keys = [k.title() for k in bot.db.get_nick_value(user, "pkskeys").split("#")]
        outkeys = []
        for k in keys:
            if k[0] is not '!' or trigger.nick == user:
                outkeys.append(k)
        bot.notice("{} has the following keys: ".format(user) + ", ".join(outkeys))
        return
    elif key is not None:
        key = key.lower()
        if key[0] == "@":
            return
        raw_data = bot.db.get_nick_value(user, "pks_" + key)
        data = _dataScript(raw_data, bot.db)

    if '$reader' in data:
        data = data.replace('$reader', trigger.nick)

    bot.notice("{}: {}".format(trigger.nick, data))


@module.commands('remember')
def remember(bot, trigger):
    """`.remember [flag]<key>, <data>` - Sets <key> to <data>. ! can be specified as a flag to preventa key from being listed to other users. $ctime and $cdate can be used in <data> and will be replaced with the current time (That is, when .remember is called). $time and $date will be replaced with the same, but with the time that the key is read (i.e., when .finger is called). $reader will be replaced with the nick that called .finger on the key."""
    key, val = trigger.group(2).split(",", 1)
    val = val.strip()
    key = key.strip().lower()

    if not re.match("!?[\w\s\d]{0,12}", key) or not re.match("(\w\s\d){0,150}", val):
        bot.notice("Sorry, your information may only contain alphanumerics and spaces. The key is limited to 12 characters.", trigger.nick)

    keystore = bot.db.get_nick_value(trigger.nick, "pkskeys")
    if keystore:
        keystore = keystore.split("#")
        if key not in keystore:
            keystore.append(key)
        if "@" + key in keystore:
            bot.notice("Sorry, that key is locked.", trigger.nick)
            return
    else:
        keystore = [key]

    dt = datetime.now()
    if '$time' in val:
        val = val.replace('$ctime', dt.strftime("%H:%M:%S"))

    if '$date' in val:
        val = val.replace('$cdate', dt.strftime("%d/%m/%Y"))

    if key[0] == "@":
        hashkey = "Doesn'tMatter".encode("utf-8")
        val = val.encode("utf-8")
        val = hmac.new(hashkey, msg=val, digestmod="SHA256").hexdigest()

    bot.db.set_nick_value(trigger.nick, "pkskeys", "#".join(keystore))

    bot.db.set_nick_value(trigger.nick, "pks_" + key, val)

    bot.notice("Added key {} with data {}".format(key, val), trigger.nick)


@module.commands('forget')
def forget(bot, trigger):
    """`.forget <key>`- Remove <key> from your file."""
    key = trigger.group(2)
    if len(key.split(" ")) > 1:
        key, passw = trigger.group(2).split(" ")

    key = key.lower()

    keystore = bot.db.get_nick_value(trigger.nick, "pkskeys")
    if keystore:
        keystore = keystore.split("#")
        if key in keystore and "@"+key not in keystore:
            keystore.remove(key)
    bot.db.set_nick_value(trigger.nick, "pkskeys", "#".join(keystore))
    bot.db.set_nick_value(trigger.nick, "pks_" + key, None)
    bot.notice("Removed key {}.".format(key), trigger.nick)

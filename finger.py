import sopel.module as module
import re
from datetime import datetime


def _dataScript(s, db, stack=None):
    data = s
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
        data = data.replace('$time', dt.strftime("%H%M%S"))

    if '$date' in data:
        data = data.replace('$date', dt.strftime("%d%m%Y"))

    sub = re.findall("\{([\w\s\d]+)\:([\w\s\d]{0,12})\}", data)
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


@module.commands('finger', 'f')
def finger(bot, trigger):
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

    if key is None:
        keys = [k.title() for k in bot.db.get_nick_value(user, "pkskeys").split("#")]
        outkeys = []
        for k in keys:
            if k[0] is not '!':
                outkeys.append(k)
        bot.notice("{} has the following keys: ".format(user) + ", ".join(outkeys))
        return
    else:
        key = key.lower()
        raw_data = bot.db.get_nick_value(user, "pks_" + key)
        data = _dataScript(raw_data, bot.db)

    if '$reader' in data:
        data = data.replace('$reader', trigger.nick)

    bot.notice("{}: {} {}".format(trigger.nick, key.title(), data))


@module.commands('remember', 'r')
def remember(bot, trigger):
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
    else:
        keystore = [key]

    bot.db.set_nick_value(trigger.nick, "pkskeys", "#".join(keystore))

    bot.db.set_nick_value(trigger.nick, "pks_" + key, val)

    bot.notice("Added key {} with data {}".format(key, val), trigger.nick)


@module.commands('forget', 'f')
def forget(bot, trigger):
    key = trigger.group(2).lower()

    keystore = bot.db.get_nick_value(trigger.nick, "pkskeys")
    if keystore:
        keystore = keystore.split("#")
        if key in keystore:
            keystore.remove(key)
    bot.db.set_nick_value(trigger.nick, "pkskeys", "#".join(keystore))
    bot.db.set_nick_value(trigger.nick, "pks_" + key, None)
    bot.notice("Removed key {}.".format(key), trigger.nick)

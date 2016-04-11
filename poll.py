import sqlite3
import datetime
import sopel.module as module
from sopel.config.types import StaticSection, ValidatedAttribute, FilenameAttribute

class PollSection(StaticSection):
    dbname = FilenameAttribute('dbname', default="./poll.db")

@module.commands('polllist', 'polll')
def list(bot, trigger):
    """Lists active polls."""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    now = datetime.datetime.now()
    c.execute('''SELECT ROWID,question FROM polls WHERE expires > ?''', (now,))
    for row in c:
        bot.say("[POLL] {}: {}".format(row[0], row[1]))

@module.commands('polldisplay', 'polld')
def display(bot, trigger):
    """Displays a poll and its options. .polld <poll_id>"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    args = trigger.group(2)
    try:
        int(args)
    except:
        bot.say("Invalid poll ID")
        return

    c.execute('''SELECT owner,question FROM polls WHERE ROWID = ?''', (args,))
    owner,question = c.fetchone()
    if owner is None:
        bot.say("Invalid poll ID")
        return

    c.execute('''SELECT response,rid FROM responses WHERE poll = ?''', (args,))

    bot.say("[POLL] {} asks: {}".format(owner, question))
    for row in c:
        bot.say("[POLL] {}: {}".format(row[1], row[0]))

@module.commands('pollresults')
@module.commands('pollr')
@module.example('.pollresults 1')
def results(bot, trigger):
    """Check the results for each option in a poll. .pollr <poll_id>"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    #poll rid response count

    args = trigger.group(2)
    try:
        int(args)
    except:
        bot.say("Invalid poll ID")
        return

    poll = int(args)

    c.execute('''SELECT COUNT(*),question FROM polls WHERE ROWID = ?''', (poll,))
    row = c.fetchone()
    if row[0] != 1:
        bot.say("Invalid poll ID")
    bot.say("[POLL] Responses for {}:".format(row[1]))

    c.execute('''SELECT * FROM RESPONSES WHERE poll = ?''', (poll,))
    responses = []
    total_responses = 0
    for row in c:
        responses.append((row[2],row[3]))
        total_responses = total_responses + int(row[3])

    for resp in responses:
        bot.say("[POLL] {}: {} / {} ({}%)".format(resp[0], resp[1], total_responses, resp[1]*100/total_responses))

    
@module.commands('delete')
@module.require_admin()
def remove(bot, trigger):
    """Remove a poll from the database. Also deletes the results"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    db.commit()
    db.close()

@module.commands('pollstart')
@module.commands('polls')
@module.example('.pollstart 1 10')
@module.require_chanmsg()
def start(bot, trigger):
    """Start a poll, allowing users to vote in it. .polls <poll_id> <time_in_minutes>"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    args = trigger.group(2)
    if not args:
        bot.say("You must specify a poll ID and poll time (in minutes).")
    
    poll, tdelta = args.split(" ")
    tdelta = datetime.timedelta(minutes = int(tdelta))
    time = datetime.datetime.now() + tdelta
    c.execute("SELECT question FROM polls WHERE ROWID = ? AND owner = ? AND expires = 0", (poll, trigger.nick))
    p = c.fetchone()
    
    if p is None:
        bot.say("No such poll with ID {} (It might not be your poll)".format(poll))
        return

    c.execute("UPDATE polls SET expires = ? WHERE ROWID = ?", (time, poll))
    c.execute("SELECT response, rid FROM responses WHERE poll = ? ORDER BY rid ASC", (poll,))

    bot.say("{} has started a poll that expires in {}. Cast your vote with '.pollvote {} [choice]".format(trigger.nick, tdelta, poll))
    bot.say("[POLL] {} asks: {}".format(trigger.nick, p[0]))
    
    for row in c:
        bot.say("[POLL] {}: {}".format(row[1], row[0]))

    db.commit()
    db.close()

@module.commands('pollcreate')
@module.commands('pollc')
@module.example('.pollcreate What\'s your favorite color?')
@module.require_privmsg()
def create(bot, trigger):
    """Register a new poll with question text. .pollc <question>"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    text = trigger.group(2)

    c.execute("INSERT INTO polls VALUES(?, ?, 0);", (trigger.nick, text))
    bot.say("Poll ID {} created with question {}".format(c.lastrowid, text))

    db.commit()
    db.close()

@module.commands('pollo')
@module.example('.polloption 1 Blue')
@module.require_privmsg(message="Polls must be modified in private messages.")
def option(bot, trigger):
    """Add a response option to a poll. .pollo <poll_id> <response>"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    args = trigger.group(2)
    poll, text = args.split(" ", 1)
    
    c.execute("SELECT COUNT(*) FROM responses WHERE poll = ?", (poll,))
    count = c.fetchone()[0]
    if count == 0:
        c.execute("SELECT COUNT(*) FROM polls WHERE ROWID = ? AND owner = ?", (poll, trigger.nick))
        res = c.fetchone()
        if res[0] == 0:
            bot.say("Either you don't own that poll or it doesn't exist.")
            return
    
    if count == 6:
        bot.say("No more than 6 options.")
        return


    c.execute("INSERT INTO responses VALUES(?, ?, ?, 0)", (poll, count+1, text))
    bot.say("Added response: {}".format(text))
    db.commit()
    db.close()

@module.commands('pollvote')
@module.commands('pollv')
@module.example('.pollvote 1 2')
def vote(bot, trigger):
    """Cast your vote in a poll. .pollv <poll_id> <response>"""
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()

    args = trigger.group(2)
    if(len(args.split(" ")) != 2):
        bot.say("Proper usage: .pollvote <poll_id> <poll_option>")
        return

    poll, opt = args.split(" ")

    c.execute("SELECT COUNT(*) FROM voters WHERE poll = ? AND nick = ?", (poll, trigger.nick))
    res = c.fetchone()
    if res[0] != 0:
        bot.say("You've already voted in this poll.")
        return

    time = datetime.datetime.now()
    c.execute("SELECT COUNT(*) FROM polls WHERE ROWID = ? AND expires > ?", (poll, time))
    res = c.fetchone()
    if res[0] == 0:
        bot.say("No such poll with id {}.".format(poll))
        return

    c.execute("SELECT count FROM responses WHERE poll = ? AND rid = ?", (poll, opt))
    res = c.fetchone()
    if res is None:
        bot.say("No such poll response with choice number {}.".format(opt))
        return

    c.execute("UPDATE responses SET count = ? WHERE poll = ? AND rid = ?", (res[0]+1, poll, opt))
    c.execute("INSERT INTO voters VALUES(?, ?)", (trigger.nick, poll))
    
    db.commit()
    db.close()
    bot.say("Vote recorded!")

def setup(bot):
    bot.config.define_section('poll', PollSection)
    db = sqlite3.connect(bot.config.poll.dbname, detect_types=sqlite3.PARSE_DECLTYPES)
    c = db.cursor()
    c.execute('''CREATE TABLE if not exists polls (owner text, question text, expires timestamp)''')
    c.execute('''CREATE TABLE IF NOT EXISTS responses (poll int, rid int, response text, count int)''')
    c.execute('''CREATE TABLE IF NOT EXISTS voters (nick text, poll int)''')
    db.commit()
    db.close()

def configure(config):
    config.define_section('poll', PollSection, validate = False)
    config.poll.configure_setting(
        'dbname',
        'Enter a filename for the poll database.',
    )

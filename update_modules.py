import sopel.module as module
import git

@module.commands('gitpull')
@module.require_admin()
def pull(bot, trigger):
	g = git.cmd.Git('/home/quartermaster/.sopel/modules')
	res = g.pull()
	bot.say(res)

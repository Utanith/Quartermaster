#!/usr/bin/python3
from datetime import date
import sqlite3
from sopel.config.types import (
		StaticSection, FilenameAttribute, ValidatedAttribute
	)
import sopel.module as module


@module.commands('take')
@module.example('')
def take(bot, trigger):
	pass

@module.commands('drop')
def drop(bot, trigger):
	pass

@module.commands('wear')
def wear(bot, trigger):
    pass

@module.commands('use')
def use(bot, trigger):
    pass

@module.commands('look')
def look(bot, trigger):
    pass

class Game():
    players = []
    rooms = []

    def __init__(self):
        pass


class Player():
    def __init__(self, player):
        self.player = player
        self.inventory = []
        self.equip = []
        self.room = None

    def addItem(self, item):
        if item.name in self.room.inventory:
            self.inventory.append(item.name)
            room.inventory.remove(item.name)

    def useItem(self, item):
        if item.name in self.inventory:
            item.use(self)
            self.inventory.remove(item)

    def dropItem(self, item):
        if item.name in self.inventory and item.usable:
            self.inventory.remove(item)
            # Put item on the floor

    def equipItem(self, item):
        if item.name in self.inventory and item.equipable:
            self.equip.append(item.name)
            self.inventory.remove(item.name)

    def unequipItem(self, item):
        if item.name in self.equp:
            self.inventory.append(item.name)
            self.equip.remove(item.name)




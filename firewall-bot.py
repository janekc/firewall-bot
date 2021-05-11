# -*- coding: utf-8 -*-
from deltabot.hookspec import deltabot_hookimpl
from deltabot import DeltaBot
from deltachat import Chat, Contact, Message
import socket
import pyufw as ufw
import segno


version = '0.7'

# ======== Hooks ===============

@deltabot_hookimpl
def deltabot_init(bot):
    global  
    dbot = bot

    bot.commands.register(name="/enable", func=cmd_enable)
    bot.commands.register(name="/disable", func=cmd_disable)
    bot.commands.register(name="/reset", func=cmd_reset)
    bot.commands.register(name="/status", func=cmd_status)
    bot.commands.register(name="/setdefault", func=cmd_setdefault)
    bot.commands.register(name="/add", func=cmd_add)
    bot.commands.register(name="/delete", func=cmd_delete)
    bot.commands.register(name="/getrules", func=cmd_getrules)
    bot.commands.register(name="/showlistening", func=cmd_showlistening)
    bot.commands.register(name="/setlogging", func=cmd_setlogging)
    bot.commands.register(name="/guided", func=cmd_guided)


@deltabot_hookimpl
def deltabot_start(bot: DeltaBot, chat = Chat):
    """
    Runs every time the bot starts and checks if it was already set up.
    If not, print a QR-code to terminal. Admins can scan it and get added to an admingroup.
    Where Members can send commands to the bot.
    """
    if dbot.get("issetup") == "yes!" and dbot.get("admgrpid") != '':
        print("Admingroup found")
    else:
        dbot.logger.warn("Creating an admin group")
        chat = dbot.account.create_group_chat("Admin group on {}".format(socket.gethostname()), contacts=[], verified=True)
        dbot.set("admgrpid",chat.id)
        dbot.get("issetup", "yes!")
        qr = segno.make(chat.get_join_qr())
        print("\nPlease scan this qr code to join a verified admin group chat:\n\n")
        qr.terminal()


# ======== Commands ===============

def cmd_enable(command, replies):
    """
    Enables the ufw firewall and enables on boot.
    """
    if check_priv(dbot, command.message):
        dbot.logger.info("\nEnabling the firewall!\n")
        ufw.enable()
        replies.add("Firewall enabled!")


def cmd_disable(command, replies):
    """
    Disables the ufw firewall and disables on boot.
    """
    if check_priv(bot, command.message):
        dbot.logger.info("\nDisabling the firewall!\n")
        ufw.disable()
        replies.add("Firewall disabled!")


def cmd_reset(command, replies):
    """
    Returns the firewall to it's install defaults. incoming=deny, outgoing=allow, routed=reject
    The default rules are:
    allow SSH
    allow to 224.0.0.251 app mDNS
    """
    if check_priv(dbot, command.message):
        dbot.logger.info("\nResetting the firewall!\n")
        ufw.reset()
        replies.add("Reset complete! \nDefault rules: \nallow SSH \nallow to 224.0.0.251 app mDNS")


def cmd_status(command, replies):
    """
    Retuns a dict. Status is either 'active' or 'inactive'. If the firewall is active the default policies and rules list will also be included.
    """
    if check_priv(dbot, command.message):
        replies.add(ufw.status())


def cmd_setdefault(command, replies):
    """
    Set the default policies for incoming, outgoing and routed. Policies to choose from are allow, deny and reject.

    TODO: build logic for reject, allow , deny
    """
    if check_priv(dbot, command.message):
        if command.payload.split() == len(3):
            incoming, outgoing, routedds = command.payload.split()
            print(incoming, outgoing, routedds)
            #ufw.default(incoming, outgoing, routedds)


def cmd_add(command, replies):
    """
    Add or Insert a rule. To insert a rule you can specify a rule number but this is optional.
    Check out man ufw for rule syntax.
    Returns the raw iptables rule added (incase your interested)
    """
    if check_priv(dbot, command.message):
        rule = ufw.add(command.payload)
        dbot.logger.info("\n\Added Rule:\n{}\n".format(rule))
        replies.add("The following iptables rule was added:\n{}".format(rule))


def cmd_delete(command, replies):
    """
    Delete a rule. You can specify the rule itself, the rule number or the string * to delete all rules.
    """
    if check_priv(dbot, command.message):
        ufw.delete(command.payload)
        dbot.logger.info("\n\Deleted rule:\n{}\n".format(command.payload))
        replies.add("Deleted rule {}".format(command.payload))


def cmd_getrules(command, replies):
    """
    Get a list of the current rules. Returns a dict with the rule numbers as the index.
    """
    if check_priv(dbot, command.message):
        replies.add(ufw.get_rules())


def cmd_showlistening(command, replies):
    """
    Returns an array of listening ports, applications and rules that apply.
    Array contains a series of tuples of the following structure:
    (str transport, str listen_address, int listen_port, str application, dict rules)
    """
    if check_priv(dbot, command.message):
        replies.add(ufw.show_listening())


def cmd_setlogging(command, replies):
    """
    Set the ufw logging level. Choose from: 'on', 'off', 'low', 'medium', 'high', 'full'. Check out man ufw for more info on logging.
    """
    if check_priv(dbot, command.message):
        if command.payload in ['on','off','low','medium','high','full']:
            print("right")
            ufw.set_logging(command.payload)
        else:
            replies.add("please specify one of the following options: on,off,low,medium,high,full")


def cmd_guided(command, replies):
    """
    Guided use of the firewall-chatbot
    """
    if check_priv(dbot, command.message):
        pass


# ======== Utilities ===============

def check_priv(bot, message):
    if message.chat.is_group() and int(dbot.get('admgrpid')) == message.chat.id:
            if message.chat.is_protected() and int(message.chat.num_contacts) >= 2:
                return True
    dbot.logger.error("recieved message from wrong or not protected chat.")
    dbot.logger.error("Sender: {}".format(message.get_sender_contact().addr))
    dbot.logger.error("Chat: {}".format(message.chat.get_name()))
    dbot.logger.error("Message: {}".format(message.text))
    return False
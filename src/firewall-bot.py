# -*- coding: utf-8 -*-
from deltabot.hookspec import deltabot_hookimpl
import pyufw as ufw
import segno


version = '0.6'

# ======== Hooks ===============

@deltabot_hookimpl
def deltabot_init(bot):
    bot.commands.register(name="/echo", func=cmd_echo)
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
def deltabot_start(chat):
    """
    Runs every time the bot starts and checks if it was already set up.
    If not, print a QR-code to terminal. Admins can scan it and get added to an admingroup.
    Where Members can send commands to the bot.
    """
    if  check_priv(dbot, chat):
        dbot.logger.warn("Found Admingroup")
    else:
        dbot.logger.warn("Creating an admin group")
        chat = dbot.account.create_group_chat("Admin group on {}".format(socket.gethostname()), contacts=[], verified=True)
        dbot.set("admgrpid",chat.id)
        qr = segno.make(chat.get_join_qr())
        print("\nPlease scan this qr code to join a verified admin group chat:\n\n")
        qr.terminal()


# ======== Commands ===============

def cmd_echo(command, replies):
    """ Echoes back received message.

    To use it you can simply send a message starting with
    the command '/echo'. Example: `/echo hello world`
    """
    message = command.message
    contact = message.get_sender_contact()
    sender = 'From: {} <{}>'.format(contact.display_name, contact.addr)
    replies.add(text="{}\n{!r}".format(sender, command.payload))


def cmd_enable(command, replies):
    """
    Enables the ufw firewall and enables on boot.
    """
    if check_priv(bot, command.message):
        ufw.enable()


def cmd_disable(command, replies):
    """
    Disables the ufw firewall and disables on boot.
    """
    if check_priv(bot, command.message):
        ufw.disable()


def cmd_reset(command, replies):
    """
    Returns the firewall to it's install defaults. incoming=deny, outgoing=allow, routed=reject
    The default rules are:
    allow SSH
    allow to 224.0.0.251 app mDNS
    """
    if check_priv(bot, command.message):
        ufw.reset()


def cmd_status(command, replies):
    """
    Retuns a dict. Status is either 'active' or 'inactive'. If the firewall is active the default policies and rules list will also be included.
    """
    if check_priv(bot, command.message):
        replies.add(ufw.status())


def cmd_setdefault(command, replies):
    """
    Set the default policies for incoming, outgoing and routed. Policies to choose from are allow, deny and reject.
    """
    if check_priv(bot, command.message):
        pass


def cmd_add(command, replies):
    """
    Add or Insert a rule. To insert a rule you can specify a rule number but this is optional.
    Check out man ufw for rule syntax.
    Returns the raw iptables rule added (incase your interested)
    """
    if check_priv(bot, command.message):
        pass


def cmd_delete(command, replies):
    """
    Delete a rule. You can specify the rule itself, the rule number or the string * to delete all rules.
    """
    if check_priv(bot, command.message):
        pass


def cmd_getrules(command, replies):
    """
    Get a list of the current rules. Returns a dict with the rule numbers as the index.
    """
    if check_priv(bot, command.message):
        pass


def cmd_showlistening(command, replies):
    """
    Returns an array of listening ports, applications and rules that apply.
    Array contains a series of tuples of the following structure:
    (str transport, str listen_address, int listen_port, str application, dict rules)
    """
    if check_priv(bot, command.message):
        pass


def cmd_setlogging(command, replies):
    """
    Set the ufw logging level. Choose from: 'on', 'off', 'low', 'medium', 'high', 'full'. Check out man ufw for more info on logging.
    """
    if check_priv(bot, command.message):
        pass


def cmd_guided(command, replies):
    """
    Guided use of the firewall-chatbot
    """
    if check_priv(bot, command.message):
        pass


# ======== Utilities ===============

def check_priv(bot, chat):
    if chat.is_group() and int(dbot.get('admgrpid')) == chat.id:
            if chat.is_protected() and int(chat.num_contacts) >= 2:
                return True
    dbot.logger.error("recieved message from wrong or not protected chat.")
    dbot.logger.error("Sender: {}".format(chat.get_sender_contact().addr))
    dbot.logger.error("Chat: {}".format(chat.get_name()))
    dbot.logger.error("Message: {}".format(chat.message.text))
    return False
# -*- coding: utf-8 -*-
from deltabot.hookspec import deltabot_hookimpl
from deltabot import DeltaBot
from deltachat import Chat, Contact, Message
import socket
import pyufw as ufw
import segno
import json

version = "0.7"

# ======== Hooks ===============


@deltabot_hookimpl
def deltabot_init(bot):
    global dbot
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
    bot.commands.register(name="/overview", func=cmd_sysOverView)
    bot.commands.register(name="/open", func=cmd_sysopen)
    bot.commands.register(name="/next", func=cmd_sysopen)
    bot.commands.register(name="/create", func=cmd_syscreate)
    bot.commands.register(name="/skip", func=cmd_syskip)
    bot.commands.register(name="/allow", func=cmd_allowOrdeny)
    bot.commands.register(name="/deny", func=cmd_allowOrdeny)
    bot.commands.register(name="/out", func=cmd_InOutOrSkip)
    bot.commands.register(name="/in", func=cmd_InOutOrSkip)
    bot.commands.register(name="/-", func=cmd_InOutOrSkip)
    bot.commands.register(name="/from", func=cmd_from)
    bot.commands.register(name="/-from", func=cmd_fromSkip)
    bot.commands.register(name="/to", func=cmd_to)
    bot.commands.register(name="/-to", func=cmd_toSkip)
    bot.commands.register(name="/port", func=cmd_port)
    bot.commands.register(name="/-port", func=cmd_portSkip)
    bot.commands.register(name="/yes", func=command_correct)
    bot.commands.register(name="/no", func=command_correct)


@deltabot_hookimpl
def deltabot_start(bot: DeltaBot, chat=Chat):
    """
    Runs every time the bot starts and checks if it was already set up.
    If not, print a QR-code to terminal. Admins can scan it and get added to an admingroup.
    Where Members can send commands to the bot.
    """
    if dbot.get("issetup") == "yes!" and dbot.get("admgrpid") != "":
        print("Admingroup found")
    else:
        dbot.logger.warn("Creating a firewall-bot group")
        chat = dbot.account.create_group_chat(
            "Admin group on {}".format(socket.gethostname()), contacts=[], verified=True
        )
        dbot.set("admgrpid", chat.id)
        dbot.set("issetup", "yes!")
        qr = segno.make(chat.get_join_qr())
        print(
            "\nPlease scan this qr code with your deltachat client to join a verified firewall-bot group chat:\n\n"
        )
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
    if check_priv(dbot, command.message):
        dbot.logger.info("\nDisabling the firewall!\n")
        ufw.disable()
        replies.add("Firewall disabled!")


# ======== Kommentar zu 'cmd_reset': Löscht zwar alle existierenden Regeln jedoch auch BEFORE Rules in /etc/ufw die zum aussperren führen könnten ====
# ======== Außerdem wird nicht dafür gesorgt, dass SSH und mDNS erlaubt wird. --> RESET löschen? :) ? ===============================


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
        replies.add(
            "Reset complete! \nDefault rules: \nallow SSH \nallow to 224.0.0.251 app mDNS"
        )


def cmd_status(command, replies):
    """
    Retuns a dict. Status is either 'active' or 'inactive'. If the firewall is active the default policies and rules list will also be included.
    """
    if check_priv(dbot, command.message):
        status = ufw.status()
        if status["status"] == "active":
            rules = "\n"
            for rule in status["rules"].keys():
                rules = rules + "- {}: {}\n".format(rule, status["rules"][rule])

            replies.add(
                "status: {} \n\ndefault tables:\n- incoming: {}\n- outgoing: {}\n- routed: {} \n\nrules: {}".format(
                    status["status"],
                    status["default"]["incoming"],
                    status["default"]["outgoing"],
                    status["default"]["routed"],
                    rules,
                )
            )
        else:
            replies.add("status: {}".format(status["status"]))


# =========== Man kann sich mit 'cmd_setdefault' aussperren ============
def cmd_setdefault(command, replies):
    """
    Set the default policies for incoming, outgoing and routed. Policies to choose from are allow, deny and reject.
    """
    if check_priv(dbot, command.message):
        if len(command.payload.split(",")) == 3:
            options = ["reject", "allow", "deny"]
            incoming, outgoing, routedds = command.payload.split(",")
            outgoing = outgoing.strip()
            routedds = routedds.strip()
            if incoming in options and outgoing in options and routedds in options:
                ufw.default(incoming, outgoing, routedds)
                dbot.logger.info(
                    "\nChanged default tables to: incoming: {} outgoing: {} routed: {}\n".format(
                        incoming, outgoing, routedds
                    )
                )
                replies.add(
                    "Changed default tables to:\n\nincoming: {}\noutgoing: {}\n routed: {}".format(
                        incoming, outgoing, routedds
                    )
                )
                return
        replies.add(
            "Please specify one of these options allow/deny/reject for the default tables in the following order: incoming, outgoing, routed"
        )


def cmd_add(command, replies):
    """
    Add or Insert a rule. To insert a rule you can specify a rule number but this is optional.
    Check out man ufw for rule syntax.
    Returns the raw iptables rule added (incase your interested)
    """
    if check_priv(dbot, command.message):
        # var 'rule' wird nicht verwendet
        rule = ufw.add(command.payload)
        dbot.logger.info("\nAdded Rule:\n{}\n".format(command.payload))
        replies.add(
            "The following iptables rule was added:\n{}".format(command.payload)
        )


def cmd_delete(command, replies):
    """
    Delete a rule. You can specify the rule itself, the rule number or the string * to delete all rules.
    """
    if check_priv(dbot, command.message):
        ufw.delete(command.payload)
        dbot.logger.info("\nDeleted rule:\n{}\n".format(command.payload))
        replies.add("Deleted rule: {}".format(command.payload))


def cmd_getrules(command, replies):
    """
    Get a list of the current rules. Returns a dict with the rule numbers as the index.
    """
    if check_priv(dbot, command.message):
        rules = ""
        rulesans = ufw.get_rules()
        for rule in rulesans.keys():
            rules = rules + "- {}: {}\n".format(rule, rulesans[rule])
        replies.add(rules)


def cmd_showlistening(command, replies):
    """
    Returns an array of listening ports, applications and rules that apply.
    Array contains a series of tuples of the following structure:
    (str transport, str listen_address, int listen_port, str application, dict rules)
    """
    if check_priv(dbot, command.message):
        replies.add("".format(ufw.show_listening()))


def cmd_setlogging(command, replies):
    """
    Set the ufw logging level. Choose from: 'on', 'off', 'low', 'medium', 'high', 'full'. Check out man ufw for more info on logging.      ===============================
    """
    if check_priv(dbot, command.message):
        if command.payload in ["on", "off", "low", "medium", "high", "full"]:
            ufw.set_logging(command.payload)
            dbot.logger.info("\nSet logging level to:{}\n".format(command.payload))
            replies.add("Set logging level to: {}\n".format(command.payload))
        else:
            replies.add(
                "please specify one of the following options: on,off,low,medium,high,full"
            )


# ======== Guided Mode Commands ===============

UFW_CMD = {"cmd1": "", "cmd2": "", "cmd3": "", "cmd4": "", "cmd5": ""}
SYS_UFW = ""
System = {"Protocol": "", "Address": "", "Port": "", "Service": "", "ExistingRule": ""}


def cmd_guided(command, replies):
    """
    Guided use of the firewall-chatbot. With the command /guided you can start the Guided Mode.
    """
    if check_priv(dbot, command.message):
        dbot.logger.info("\nStarted the Guided Mode!\n")
        replies.add(
            "Started Guided Mode. What do you want to do with the Firewall?\n\nIf you first want to have an overview of your system and its services write /overview. \n\nBut if you want to create a new rule directly \n\n please type /allow /deny or /reject instead."
        )


def cmd_sysOverView(command, replies):
    """
    With this command the bot will show you listening ports, applications and rules that apply on this system.
    """
    if check_priv(dbot, command.message):

        dbot.logger.info("\nStarted Systemscan\n")
        sysover = ufw.show_listening()
        next = 1
        for sys in sysover:
            System["Protocol"] = sys[0]
            if sys[1] == "*":
                System["Address"] = "all"
            else:
                System["Address"] = sys[1]
            System["Port"] = sys[2]
            System["Service"] = sys[3]
            if not sys[-1]:
                System["ExistingRule"] = "No"
            else:
                System["ExistingRule"] = sys[-1]
            sysoverSorted = json.dumps(System, indent=2, sort_keys=False)
            dbot.logger.info("Your System: {} \n\n {}".format(sysover, type(sysover)))
            replies.add(
                "{}. System: {}\n\n if you want to open something from your system type /open\n".format(
                    next, sysoverSorted
                )
            )
            next += 1


def cmd_sysopen(command, replies):
    """
    With this command you will be asked if you want to create an allow rule to open the first listening port that does not currently have a rule in your firewall.
    """
    global SYS_UFW

    if check_priv(dbot, command.message):
        sysover = ufw.show_listening()
        for sys in sysover:
            rule = sys[-1]
            if not rule:
                SYS_UFW = str(sys[2])
                replies.add(
                    "Do you want open port {} to be reachable for service {}? Type /create to create this new rule or /skip if you want to do something specific.".format(
                        str(sys[2]), str(sys[3])
                    )
                )
                break


def cmd_syscreate(command, replies):
    """
    With this command you say that you want to create a rule for this listening port.
    """
    global SYS_UFW
    if check_priv(dbot, command.message):
        rule = "allow " + SYS_UFW
        ufw.add(rule)
        replies.add(
            f"\n\nCreated new Rule: {rule}! to check the next listening port type /next"
        )


def cmd_syskip(command, replies):
    """
    This command skips the currently listening port, and the bot then asks you to the next listening port if you want to set up a rule for that port.
    """
    global SYS_UFW
    if check_priv(dbot, command.message):
        sysover = ufw.show_listening()
        for index, sys in enumerate(sysover):
            next = index + 1
            if next < len(sysover):
                nxtsys = sysover[next]
                rule = nxtsys[-1]
                if not rule:
                    SYS_UFW = str(sys[2])
                    replies.add(
                        "\n\nSkipped Port {}!\n\n Do you want open port {} to be reachable for service {}? Type /create to create this new rule or /skip if you want to do something specific.".format(
                            SYS_UFW, str(nxtsys[2]), str(nxtsys[3])
                        )
                    )
                    SYS_UFW = str(nxtsys[2])
                    break
            else:
                replies.add(
                    "\n\nSkipped Port {}!\n\n You have no more listening ports on your system to open. If you want to create another rule then write either /allow /deny or /reject to continue with the Guided Mode.".format(
                        SYS_UFW
                    )
                )


def cmd_allowOrdeny(command, replies):
    """
    With the /allow, /deny or /reject command you can tell the bot what you want to set up for a new rule. The difference between reject and deny is that with reject the sender of the network packet receives a message that it has been rejected.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd1"] = command.message.text.strip("/") + " "
        replies.add(
            "Do you want to {} Incoming or Outgoing Traffic?\n\n Please type /in, /out or /- to skip".format(
                UFW_CMD["cmd1"]
            )
        )


def cmd_InOutOrSkip(command, replies):
    """
    With /in, /out or /- is defined which kind of traffic it is. outgoing (/out) or incoming (/in). With the command /- (stands for skip) you can skip this step. By default, incoming traffic is assumed.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        if (
            command.message.text.strip() == "/in"
            or command.message.text.strip() == "/out"
        ):
            UFW_CMD["cmd2"] = command.message.text.strip("/") + " "
            replies.add(
                "Do you have an specific IP-address from which you will {}traffic?\n\n Please type the /from IP-address or \n /-from if you want to skip".format(
                    UFW_CMD["cmd1"]
                )
            )

        if command.message.text.strip() == "/-":
            UFW_CMD["cmd2"] = ""
            replies.add(
                "Do you have an specific IP-address from which you will {}traffic?\n\n Please type the /from IP-address or \n /-from if you want to skip".format(
                    UFW_CMD["cmd1"]
                )
            )


def cmd_from(command, replies):
    """
    With /from you can specify an IP-address from which traffic is accepted or denied.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd3"] = "from " + command.payload + " "
        replies.add(
            "Do you have an specific IP-address to which you will {}traffic?\n\n Please type the /to IP-address or /-to if you want to skip".format(
                UFW_CMD["cmd1"]
            )
        )


def cmd_fromSkip(command, replies):
    """
    With /-from you can skip the 'from IP-address' step.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd3"] = "from any "
        replies.add(
            "Do you have an specific IP-address to which you will {}traffic?\n\n Please type the /to IP-Address or /-to if you want to skip".format(
                UFW_CMD["cmd1"]
            )
        )


def cmd_to(command, replies):
    """
    With /to you can specify an IP-address to which traffic is accepted or denied.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd4"] = "to " + command.payload + " "
        replies.add(
            "Do you have an specific Port to {}?\n\n Please type the /port Portnumber, Portnumber2 or /-port if you want to skip".format(
                UFW_CMD["cmd1"]
            )
        )


def cmd_toSkip(command, replies):
    """
    With /-to you can skip the 'to IP-address' step.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd4"] = "to any "
        replies.add(
            "Do you have an specific Port to {}?\n\n Please type the /port Portnumber, Portnumber2 or /-port if you want to skip".format(
                UFW_CMD["cmd1"]
            )
        )


def cmd_port(command, replies):
    """
    With /port you can specify an port for the new rule.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd5"] = "port " + command.payload
        ufwcommand = command_build()
        dbot.logger.info("Build follow command: {}".format(ufwcommand))
        replies.add(
            "Is this command \n\n '{}' right? \n\n type /yes or /no".format(ufwcommand)
        )


def cmd_portSkip(command, replies):
    """
    With /-port you can skip the 'port' step.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        UFW_CMD["cmd5"] = ""
        ufwcommand = command_build()
        dbot.logger.info("Build follow command:\n\n {}".format(ufwcommand))
        replies.add(
            "Is this command '{}' right?\n\n type /yes or /no".format(ufwcommand)
        )


def command_build():
    global UFW_CMD
    ufwcommand = (
        UFW_CMD["cmd1"]
        + UFW_CMD["cmd2"]
        + UFW_CMD["cmd3"]
        + UFW_CMD["cmd4"]
        + UFW_CMD["cmd5"]
    )
    return ufwcommand


def command_correct(command, replies):
    """
    The /yes /no command is used to either accept the created command with /yes in the firewall or to reject it with /no.
    """
    global UFW_CMD

    if check_priv(dbot, command.message):
        if command.message.text.strip() == "/yes":
            ufwcommand = (
                UFW_CMD["cmd1"]
                + UFW_CMD["cmd2"]
                + UFW_CMD["cmd3"]
                + UFW_CMD["cmd4"]
                + UFW_CMD["cmd5"]
            )
            replies.add(
                "The Following Rule will be added to the ufw firewall:\n\n {}".format(
                    ufwcommand
                )
            )
            ufw.add(ufwcommand)
        if command.message.text.strip() == "/no":
            replies.add("Please start the Guided Mode again")


# ======== Utilities ===============


def check_priv(bot, message):
    if message.chat.is_group() and int(dbot.get("admgrpid")) == message.chat.id:
        if message.chat.is_protected():
            return True
    dbot.logger.error("recieved message from wrong or not protected chat.")
    dbot.logger.error("Sender: {}".format(message.get_sender_contact().addr))
    dbot.logger.error("Chat: {}".format(message.chat.get_name()))
    dbot.logger.error("Message: {}".format(message.text))
    return False



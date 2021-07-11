# -*- coding: utf-8 -*-
import gettext
import os
import platform
import re
import socket
from contextlib import suppress

import segno
import ufw.common as ufwc
import ufw.frontend as ufwf
import ufw.parser as ufwp
import ufw.util as ufwu
from deltabot import DeltaBot
from deltabot.hookspec import deltabot_hookimpl
from deltachat import Chat, Contact, Message

version = "0.8"


# >>> HOOKS


@deltabot_hookimpl
def deltabot_init(bot):
    global dbot
    dbot = bot
    bot.commands.unregister(name="/set")
    menu()


@deltabot_hookimpl
def deltabot_start(bot: DeltaBot, chat=Chat):
    """
    Runs every time the bot starts and checks if it was already set up.
    Prints a QR-code to terminal. Admins can scan it and get added to an admingroup.
    Where Members can send commands to the bot.
    """
    chat = None
    if dbot.get("issetup") == "yes!" and dbot.get("admgrpid") != "":
        chat = dbot.account.get_chat_by_id(int(dbot.get("admgrpid")))
        print("Admingroup found\n")
    else:
        dbot.logger.warn("Creating a firewall-bot group")
        chat = dbot.account.create_group_chat(
            f"Admin group on {host}", contacts=[], verified=True
        )
        dbot.set("admgrpid", chat.id)
        dbot.set("issetup", "yes!")
    if ufwu.get_ppid(os.getpid()) != 1:
        qr = segno.make(chat.get_join_qr())
        print(
            "\nPlease scan this qr code with your deltachat client to join a verified firewall-bot group chat:\n\n"
        )
        qr.terminal()


# >>> UTILITIES
hlp = {
    "info": "Shows system info.",
    "status": "Get and set firewall status.",
    "policy": "Get and set default policies.",
    "rules": "Get and set firewall rules.",
    "guide": "Build rules step-by-step.",
    "service": "Show listening services.",
    "scan": "Perform port-scans. (coming soon)",
}


def verify(message):
    if message.chat.is_group() and int(dbot.get("admgrpid")) == message.chat.id:
        if message.chat.is_protected():
            return True
    dbot.logger.error("recieved message from outside admingroup chat.")
    dbot.logger.error(f"sender: {message.get_sender_contact().addr}")
    dbot.logger.error(f"chat: {message.chat.get_name()}")
    dbot.logger.error(f"message: {message.text}")
    return False


def menu():
    for k, v in {"help": ("help", "h", "?"), "eval(c)": hlp.keys()}.items():
        for c in v:
            with suppress(Exception):
                dbot.commands.unregister(name=f"/{c}")
            dbot.commands.register(name=f"/{c}", func=eval(k))


def menu_off():
    for d in [("help", "h", "?"), hlp.keys()]:
        for c in d:
            with suppress(Exception):
                dbot.commands.unregister(name=f"/{c}")
            dbot.commands.register(name=f"/{c}", func=fake)


def fake(command, replies):
    """."""
    if not verify(command.message):
        return
    if command.message.text[1:].split()[0] in ("help", "h", "?"):
        replies.add("⚠️ not available in guided mode")
    else:
        replies.add("⚠️ quit guided mode first")


def fw():
    gettext.install(ufwc.programName)
    frontend = ufwf.UFWFrontend(dryrun=False)
    return (frontend, frontend.backend)


def clear_cmd():
    for c in ("/", "start", "stop", "reset", "move", "del"):
        with suppress(Exception):
            dbot.commands.unregister(name=f"/{c}")


def help(command, replies):
    """."""
    if not verify(command.message):
        return
    x = []
    for c, d in hlp.items():
        x.append(f"🔅 /{c}\n{d}")
    x.append("🔅 /help /h /?\nInvoke this menu.")
    x = "\n\n".join(x)
    replies.add(f"🌐 MENU\n\n{x}")


# >>> INFO


def info(command, replies):
    """."""
    if not verify(command.message):
        return
    host = socket.gethostname()
    ip = socket.gethostbyname(socket.getfqdn())
    lin = platform.platform()
    replies.add(
        f"🌐 SYSTEM\n🔹 Hostname:  '{host}'\n🔹 IP-address:  '{ip}'\n🔹 fwbot version:  '{version}'\n🔹 OS:  '{lin}'"
    )


# >>> STATUS


def status(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    x = "active"
    for c in ("input", "output"):
        if ufwu.cmd([fw()[1].iptables, "-L", "ufw-user-%s" % (c), "-n"])[0] == 1:
            x = "inactive"
    y = ("start", "Starts firewall and enables startup on boot.")
    if x == "active":
        y = ("stop", "Stopps firewall and disables startup on boot.")
    dbot.commands.register(name=f"/{y[0]}", func=status_set)
    replies.add(f"🌐 STATUS\n🔹 firewall:  '{x}'\n\n🔺 /{y[0]}\n{y[1]}")


def status_set(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    cmd = command.message.text[1:].split()[0]
    if cmd == "start":
        fw()[0].set_enabled(True)
    elif cmd == "stop":
        fw()[0].set_enabled(False)
    status(command, replies)


# >>> POLICY


def policy(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    x = (fw()[1]._get_default_policy(), fw()[1]._get_default_policy("output"))
    dbot.commands.register(name="//", func=policy_set)
    replies.add(
        f"🌐 POLICIES\n🔹 incoming:  '{x[0]}'\n🔹 outgoing:  '{x[1]}'\n\n🔺 //  *action*  *action*\nSet the default action for incoming (1st) and outgoing (2nd) traffic to allow, deny or reject."
    )


def policy_set(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    pl = [c for c in command.payload.split() if c.strip()]
    if len(pl) != 2:
        replies.add("⚠️ expects two arguments")
    elif not set(pl).issubset({"reject", "allow", "deny"}):
        replies.add("⚠️ arguments must be reject, allow or deny")
    else:
        for c, d in zip(("incoming", "outgoing"), pl):
            fw()[1].set_default_policy(d, c)
        if fw()[1].is_enabled():
            fw()[1].stop_firewall()
            fw()[1].start_firewall()
    policy(command, replies)


# >>> RULES


def rules(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    x = []
    for c in fw()[1].get_rules():
        x.append(f"🔹 {len(x) + 1}:  '{ufwp.UFWCommandRule.get_command(c)}'")
    dbot.commands.register(name="//", func=rules_set)
    y = "\n\n"
    z = ""
    if len(x) > 1:
        dbot.commands.register(name="/move", func=rules_set)
        z = "\n🔺 /move  *rulenumber*  *position*\nMoves an existing rule to a specific position. (experimental)\n"
    elif len(x) > 0:
        dbot.commands.register(name="/reset", func=rules_set)
        y = "\n🔺 /reset\nDelete all rules shown above.\n"
    x = "\n".join(x)
    replies.add(
        f"🌐 RULES\n{x}\n\n🔺 //  *ufw-command*\nSpecify a valid ufw-command to add or insert allow/deny/reject/limit-rules or to delete rules.\n{y}{z}\n📖 rule syntax: https://is.gd/18ivdz"
    )


# move muss überarbeitet werden, ggf. statt position angeben, ob vor oder hinter einer bestimmten rule
def rules_set(command, replies):
    """."""
    if not verify(command.message):
        return
    opt = ("allow", "deny", "reject", "limit", "delete", "insert")
    clear_cmd()
    for c in opt:
        ufwp.UFWParser().register_command(ufwp.UFWCommandRule(c))
    cmd = command.message.text[1:].split()[0]
    if "comment" in command.payload:
        plx = re.split("comment", command.payload)
        pl = [c for c in plx[0].split() if c.strip()]
        cmt = [c for c in plx[1].split() if c.strip()]
    else:
        pl = [c for c in command.payload.split() if c.strip()]
        cmt = []
    if cmd == "reset":
        while fw()[1].get_rules_count(False) > 0:
            try:
                pr = ufwp.UFWParser().parse_command(["delete", "1"])
                fw()[0].do_action(
                    pr.action, pr.data.get("rule", ""), pr.data.get("iptype", ""), True
                )
            except:
                replies.add("⛔️ ufw error (delete)")
    elif cmd == "move":
        if len(pl) != 2:
            replies.add("⚠️ expects two arguments")
        elif not all([c.isnumeric() for c in pl]):
            replies.add("⚠️ arguments must be numeric")
        else:
            x = fw()[1].get_rules_count(False)
            y = int(pl[0])
            z = int(pl[1])
            if not (y != z and 0 < y <= x and 0 < z <= x):
                # could be more elaborate
                replies.add("⚠️ invalid argument(s)")
            else:
                rle = ufwp.UFWCommandRule.get_command(
                    fw()[1].get_rules()[y - 1]
                ).split()
                print(rle)
                try:
                    pr = ufwp.UFWParser().parse_command(["delete"] + rle)
                    fw()[0].do_action(
                        pr.action,
                        pr.data.get("rule", ""),
                        pr.data.get("iptype", ""),
                        True,
                    )
                except:
                    replies.add("⛔️ ufw error (delete)")
                w = 0
                if y < z:
                    w = 1
                try:
                    pr = ufwp.UFWParser().parse_command(["insert"] + [str(z - w)] + rle)
                    fw()[0].do_action(
                        pr.action,
                        pr.data.get("rule", ""),
                        pr.data.get("iptype", ""),
                        True,
                    )
                except:
                    replies.add("⛔️ ufw error (insert)")
    else:
        if len(pl) < 2:
            replies.add("⚠️ expects arguments")
        elif pl[0] not in opt:
            replies.add("⚠️ invalid *action*")
        # add elif for insert but invalid action - length of pl has to be checked
        else:
            if cmt:
                pl.append("comment")
                pl.append(" ".join(cmt))
            try:
                pr = ufwp.UFWParser().parse_command(pl)
                print(pr)
                fw()[0].do_action(
                    pr.action, pr.data.get("rule", ""), pr.data.get("iptype", ""), True
                )
            except:
                replies.add(f"⛔️ ufw error ({pl[0]})")
    rules(command, replies)


# >>> SERVICE
serv = []
dels = []


def service(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    try:
        netstat = ufwu.parse_netstat_output(fw()[1].use_ipv6())
    except Exception:
        return
    listeners = []
    rules = fw()[1].get_rules()
    l4_protocols = list(netstat.keys())
    l4_protocols.sort()
    for transport in l4_protocols:
        if not fw()[1].use_ipv6() and transport in ["tcp6", "udp6"]:
            continue
        ports = list(netstat[transport].keys())
        ports.sort()
        for port in ports:
            for item in netstat[transport][port]:
                listen_addr = item["laddr"]
                if listen_addr.startswith("127.") or listen_addr.startswith("::1"):
                    continue
                ifname = ""
                if listen_addr == "0.0.0.0" or listen_addr == "::":
                    listen_addr = "%s/0" % (item["laddr"])
                    addr = "*"
                else:
                    ifname = ufwu.get_if_from_ip(listen_addr)
                    addr = listen_addr
                application = os.path.basename(item["exe"])
                rule = ufwc.UFWRule(
                    action="allow",
                    protocol=transport[:3],
                    dport=port,
                    dst=listen_addr,
                    direction="in",
                    forward=False,
                )
                rule.set_v6(transport.endswith("6"))
                if ifname != "":
                    rule.set_interface("in", ifname)
                rule.normalize()
                matching_rules = {}
                matching = fw()[1].get_matching(rule)
                if len(matching) > 0:
                    for rule_number in matching:
                        if rule_number > 0 and rule_number - 1 < len(rules):
                            rule = fw()[1].get_rule_by_number(rule_number)
                            rule_command = ufwp.UFWCommandRule.get_command(rule)
                            matching_rules[rule_number] = rule_command
                listeners.append(
                    (transport, addr, int(port), application, matching_rules)
                )
    x = []
    serv.clear()
    dels.clear()
    i = 0
    rl = False
    for c in listeners:
        z = c[1]
        if z == "*":
            z = "all"
        y = "None"
        if c[4]:
            y = []
            for k, v in c[4].items():
                dels.append(k)
                y.append(f"\t\t🔹 {k}:  '{v}'")
            y = "\n" + "\n".join(y)
            rl = True
        serv.append((c[0], c[1], c[2], c[3]))
        x.append(
            f"🔷 ID: {i}\n\t🔹 Service:  '{c[3]}'\n\t🔹 Protocol:  '{c[0]}'\n\t🔹 Port:  '{c[2]}'\n\t🔹 Address:  '{z}'\n\t🔹 Rules:  {y}"
        )
        i += 1
    dbot.commands.register(name="//", func=service_set)
    y = "\n\n"
    if rl:
        dbot.commands.register(name="/del", func=service_set)
        y = "\n🔺 /del  *rulenumber* \nDelete a corresponding rule.\n"
    x = "\n".join(x)
    replies.add(
        f"🌐 SERVICES\n{x}\n\n🔺 //  *action*  *ID*\nAutomagically create a corresponding rule with action allow, deny or reject. This rule will match the service as closely as possible.\n{y}\nDepending on your default profile or before rules it might not be necessary to have explicit rules for every listener."
    )


def service_set(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    cmd = command.message.text[1:].split()[0]
    pl = [c for c in command.payload.split() if c.strip()]
    if cmd == "del":
        if len(pl) != 1:
            replies.add("⚠️ expects one argument")
        elif not pl[0].isnumeric():
            replies.add("⚠️ argument must be numeric")
        elif int(pl[0]) not in dels:
            replies.add("⚠️ argument must be valid rulenumber")
        else:
            ufwp.UFWParser().register_command(ufwp.UFWCommandRule("delete"))
            try:
                pr = ufwp.UFWParser().parse_command(["delete", pl[0]])
                fw()[0].do_action(
                    pr.action, pr.data.get("rule", ""), pr.data.get("iptype", ""), True
                )
            except:
                replies.add("⛔️ ufw error (delete)")
    else:
        if len(pl) != 2:
            replies.add("⚠️ expects two arguments")
        elif pl[0] not in ("allow", "deny", "reject"):
            replies.add("⚠️ 1st argument must be allow, deny or reject")
        elif not pl[1].isnumeric():
            replies.add("⚠️ 2nd argument must be numeric")
        elif not int(pl[1]) <= len(serv):
            replies.add("⚠️ 2nd argument must be valid ID")
        else:
            ufwp.UFWParser().register_command(ufwp.UFWCommandRule(pl[0]))
            ppll = [pl[0], f"{serv[int(pl[1])][2]}/{serv[int(pl[1])][0]}"]
            if serv[int(pl[1])][1] != "*":
                ppll = [
                    pl[0],
                    "to",
                    serv[int(pl[1])][1],
                    "port",
                    str(serv[int(pl[1])][2]),
                    "proto",
                    serv[int(pl[1])][0],
                ]
            ppll.append("comment")
            ppll.append(f"auto for {serv[int(pl[1])][3]}")
            try:
                pr = ufwp.UFWParser().parse_command(ppll)
                fw()[0].do_action(
                    pr.action,
                    pr.data.get("rule", ""),
                    pr.data.get("iptype", ""),
                    True,
                )
            except:
                replies.add(f"⛔️ ufw error ({pl[0]})")
    service(command, replies)


# >>> GUIDE
gmd = ["append", "incoming", None, "any", "any", "both", "any", None]
gmc = gmd[:]


def guide_unreg(x=None):
    for c in (x, "b", "s", "/", "f", "d", "out", "src", "dst"):
        with suppress(Exception):
            dbot.commands.unregister(name=f"/{c}")


def guide_q(command, replies):
    """."""
    if not verify(command.message):
        return
    # gmc = gmd[:]
    guide_unreg("q")
    menu()
    replies.add("⚠️ guided mode cancelled")


def guide_r(i):
    z = "Position Direction Action Source Destination Protocol Port(range)s Comment"
    x = []
    for c, d, e in zip(range(8), z.split(), gmc):
        y = "🔹 "
        if c == i and c < 8:
            y = "🔸 "
        x.append(f"{y}{d}:  '{e}'")
    return "\n".join(x)


def guide(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "This mode will guide you through the creation of a firewall rule. Below you will find a list of rules as well as all possible commands.\nOnce started, you will be presented with the new rule and its default values and an indicator for which value is currently being edited.\nIf available, you may choose /s (skip) to advance to the next step (maintaining the current value or default).\n To (re-)edit a (skipped) setting, use /b (back) to go to the previous step.\nTo set a value to its default, use /d (default).\nTo exit this mode at any time, use /q (quit) - all settings done so far will be discarded.\n\nEach step will explain what is being edited as well as possible commands and arguments (in addition to /s /b /q)."
    clear_cmd()
    menu_off()
    gmc = gmd[:]
    dbot.commands.register(name="/q", func=guide_q)
    dbot.commands.register(name="/s", func=guide_0)
    x = []
    for c in fw()[1].get_rules():
        x.append(f"🔹 {len(x) + 1}:  '{ufwp.UFWCommandRule.get_command(c)}'")
    x = "\n".join(x)
    replies.add(f"🌐 GUIDE\n{txt}\n\n🌐 RULES\n{x}\n\n🔺 /s  (start)\n🔺 /q  (quit)")


def guide_0(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = f"Do you want to insert this rule at a specific position or append it at the end of all rules? (Default: append)\nRules are evaluated from top to bottom.\n\nAllowed values for *position*:  1  to  {fw()[1].get_rules_count(False)}"
    guide_unreg()
    dbot.commands.register(name="/s", func=guide_1)
    dbot.commands.register(name="//", func=guide_0_pl)
    d = ""
    if gmc[0] != gmd[0]:
        dbot.commands.register(name="/d", func=guide_0_def)
        d = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (1/8)\n{txt}\n\n{guide_r(0)}\n\n🔺 //  *position*{d}\n🔺 /s  (skip)\n🔺 /q  (quit)"
    )


def guide_0_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[0] = gmd[0]
    guide_1(command, replies)


def guide_0_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    pl = [c for c in command.payload.split() if c.strip()]
    if len(pl) != 1:
        replies.add("⚠️ expects one argument")
        guide_0(command, replies)
    elif not pl[0].isnumeric():
        replies.add("⚠️ argument must be numeric")
        guide_0(command, replies)
    elif int(pl[0]) > fw()[1].get_rules_count(False):
        replies.add("⚠️ argument must be valid position")
        guide_0(command, replies)
    else:
        gmc[0] = pl[0]
        guide_1(command, replies)


def guide_1(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "Do you want this rule to target traffic directed towards your system (incoming) or traffic originating from your system (outgoing)? (Default: incoming)\n\nDepending on the current setting, use  /out  or  /d  to switch between these options."
    guide_unreg()
    dbot.commands.register(name="/s", func=guide_2)
    dbot.commands.register(name="/b", func=guide_0)
    if gmc[1] == gmd[1]:
        dbot.commands.register(name="/out", func=guide_1_pl)
        x = "\n🔺 /out"
    else:
        dbot.commands.register(name="/d", func=guide_1_def)
        x = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (2/8)\n{txt}\n\n{guide_r(1)}\n{x}\n🔺 /b  (back)\n🔺 /s  (skip)\n🔺 /q  (quit)"
    )


def guide_1_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[1] = gmd[1]
    guide_2(command, replies)


def guide_1_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[1] = "outgoing"
    guide_2(command, replies)


def guide_2(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "Which action would you like the rule to take for the targeted traffic?\nThis setting has no default value.\n\nAllowed values for *action*:\n・ allow\n  (traffic will be accepted)\n・ deny\n  (traffic will be discarded)\n・ reject\n  (traffic will be discarded and an error paket will be returned to the sender)"
    guide_unreg()
    dbot.commands.register(name="/b", func=guide_1)
    dbot.commands.register(name="//", func=guide_2_pl)
    s = ""
    if gmc[2] != gmd[2]:
        dbot.commands.register(name="/s", func=guide_3)
        s = "\n🔺 /s  (skip)"
    replies.add(
        f"🌐 GUIDE (3/8)\n{txt}\n\n{guide_r(2)}\n\n🔺 //  *action*\n🔺 /b  (back){s}\n🔺 /q  (quit)"
    )


def guide_2_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    pl = [c for c in command.payload.split() if c.strip()]
    if len(pl) != 1:
        replies.add("⚠️ expects one argument")
        guide_2(command, replies)
    elif pl[0] not in ("allow", "deny", "reject"):
        replies.add("⚠️ argument must be allow, deny or reject")
        guide_2(command, replies)
    else:
        gmc[2] = pl[0]
        guide_3(command, replies)


def guide_3(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "***choose source"
    guide_unreg()
    dbot.commands.register(name="/b", func=guide_2)
    dbot.commands.register(name="/s", func=guide_4)
    dbot.commands.register(name="//", func=guide_3_pl)
    d = ""
    if gmc[3] != gmd[3]:
        dbot.commands.register(name="/d", func=guide_3_def)
        d = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (4/8)\n{txt}\n\n{guide_r(3)}\n\n🔺 //  *source*{d}\n🔺 /b  (back)\n🔺 /s  (skip)\n🔺 /q  (quit)"
    )


def guide_3_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[3] = gmd[3]
    guide_4(command, replies)


def guide_3_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    pl = [c for c in command.payload.split() if c.strip()]
    if len(pl) != 1:
        replies.add("⚠️ expects one argument")
        guide_3(command, replies)
    elif not ufwu.valid_address4(pl[0]):
        replies.add("⚠️ argument must be host or network")
        guide_3(command, replies)
    else:
        gmc[3] = pl[0]
        guide_4(command, replies)


def guide_4(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "***choose destination"
    guide_unreg()
    dbot.commands.register(name="/b", func=guide_3)
    dbot.commands.register(name="/s", func=guide_5)
    dbot.commands.register(name="//", func=guide_4_pl)
    d = ""
    if gmc[4] != gmd[4]:
        dbot.commands.register(name="/d", func=guide_4_def)
        d = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (5/8)\n{txt}\n\n{guide_r(4)}\n\n🔺 //  *destination*{d}\n🔺 /b  (back)\n🔺 /s  (skip)\n🔺 /q  (quit)"
    )


def guide_4_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[4] = gmd[4]
    guide_5(command, replies)


def guide_4_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    pl = [c for c in command.payload.split() if c.strip()]
    if len(pl) != 1:
        replies.add("⚠️ expects one argument")
        guide_4(command, replies)
    elif not ufwu.valid_address4(pl[0]):
        replies.add("⚠️ argument must be host or network")
        guide_4(command, replies)
    else:
        gmc[4] = pl[0]
        guide_5(command, replies)


def guide_5(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "***choose protocol"
    guide_unreg()
    dbot.commands.register(name="/b", func=guide_4)
    dbot.commands.register(name="/s", func=guide_6)
    dbot.commands.register(name="//", func=guide_5_pl)
    d = ""
    if gmc[5] != gmd[5]:
        dbot.commands.register(name="/d", func=guide_5_def)
        d = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (6/8)\n{txt}\n\n{guide_r(5)}\n\n🔺 //  *protocol*{d}\n🔺 /b  (back)\n🔺 /s  (skip)\n🔺 /q  (quit)"
    )


def guide_5_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[5] = gmd[5]
    guide_6(command, replies)


def guide_5_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    pl = [c for c in command.payload.split() if c.strip()]
    if len(pl) != 1:
        replies.add("⚠️ expects one argument")
        guide_5(command, replies)
    elif pl[0] not in ("tcp", "udp", "ah", "esp", "gre", "ipv6", "igmp"):
        replies.add("⚠️ argument must be tcp, udp, ah, esp, gre, ipv6 or igmp")
        guide_5(command, replies)
    else:
        gmc[5] = pl[0]
        guide_6(command, replies)


def guide_5_other(replies):
    txt = "***❗️must choose source or destination, use /src or /dst or go back to change protocol"
    dbot.commands.register(name="/b", func=guide_5)
    dbot.commands.register(name="/src", func=guide_3)
    dbot.commands.register(name="/dst", func=guide_4)
    replies.add(
        f"🌐 GUIDE (6/8)\n{txt}\n\n{guide_r(5)}\n\n🔺 /src  (source)\n🔺 /dst  (destination)\n🔺 /b  (back)\n🔺 /q  (quit)"
    )


def guide_6(command, replies):
    """."""
    if not verify(command.message):
        return
    guide_unreg()
    if gmc[5] == gmd[5]:
        guide_6_both(replies)
    elif gmc[5] in ("tcp", "udp"):
        guide_6_one(replies)
    elif gmc[3] == gmd[3] and gmc[4] == gmd[4]:
        guide_5_other(replies)
    else:
        guide_6_other(replies)


def guide_6_one(replies):
    txt = (
        "***choose port, multiple ports, portrange, multiple portranges or combination"
    )
    dbot.commands.register(name="/b", func=guide_5)
    dbot.commands.register(name="//", func=guide_6_one_pl)
    s = ""
    if gmc[6] != gmd[6]:
        dbot.commands.register(name="/s", func=guide_7)
        s = "\n🔺 /s  (skip)"
    replies.add(
        f"🌐 GUIDE (7/8)\n{txt}\n\n{guide_r(6)}\n\n🔺 //  *port(range)s*\n🔺 /b  (back){s}\n🔺 /q  (quit)"
    )


# duplicates and ports inside a range are okay with ufw
def guide_6_one_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    rep = ""
    repp = ["⚠️ arguments for ports must be"]
    repr = ["⚠️ arguments for portranges must be"]
    pl = [c for c in re.split(",", command.payload) if c.strip()]
    port = [c for c in pl if ":" not in c]
    range = [c for c in pl if ":" in c]
    if port:
        if not all([c.isnumeric() for c in port]):
            repp.append("numeric")
        elif any([int(c) <= 0 or int(c) > 65535 for c in port]):
            repp.append("valid portnumbers")
    if range:
        for rng in range:
            rng_items = [c for c in re.split(":", rng) if c.strip()]
            if len(rng_items) != 2:
                repr.append("two numbers separated by ':'")
                break
            elif not all([c.isnumeric() for c in rng_items]):
                repr.append("numeric")
                break
            elif rng_items[1] == rng_items[0]:
                repr.append("two different portnumbers")
                break
            elif any([int(c) <= 0 or int(c) > 65535 for c in rng_items]):
                repr.append("valid portnumbers")
                break
            elif rng_items[1] < rng_items[0]:
                repr.append("smaller number first")
                break
    if len(repp) > 1 and len(repr) > 1:
        rep = f"{' '.join(repp)}\n{' '.join(repr)}"
    elif len(repp) > 1:
        rep = " ".join(repp)
    elif len(repr) > 1:
        rep = " ".join(repr)
    if rep:
        replies.add(rep)
        guide_6_one(command, replies)
    elif pl:
        gmc[6] = command.payload
        guide_7(command, replies)
    else:
        replies.add("⚠️ expects argument")
        guide_6_one(command, replies)


def guide_6_both(replies):
    txt = "***choose exactly one port or default (default: any)"
    dbot.commands.register(name="/b", func=guide_5)
    dbot.commands.register(name="//", func=guide_6_both_pl)
    s = ""
    d = ""
    if not any(c in gmc[6] for c in (",", ":")):
        dbot.commands.register(name="/s", func=guide_7)
        s = "\n🔺 /s  (skip)"
    if gmc[6] != gmd[6]:
        dbot.commands.register(name="/d", func=guide_6_both_def)
        d = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (7/8)\n{txt}\n\n{guide_r(6)}\n\n🔺 //  *port*{d}\n🔺 /b  (back){s}\n🔺 /q  (quit)"
    )


def guide_6_both_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[6] = gmd[6]
    guide_7(command, replies)


def guide_6_both_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    pl = [c for c in re.split(",|:", command.payload) if c.strip()]
    if len(pl) != 1:
        replies.add("⚠️ expects one argument")
        guide_6_both(replies)
    elif not pl[0].isnumeric():
        replies.add("⚠️ argument must be numeric")
        guide_6_both(replies)
    elif int(pl[0]) <= 0 or int(pl[0]) > 65535:
        replies.add("⚠️ argument must be valid portnumber")
        guide_6_both(replies)
    else:
        gmc[6] = pl[0]
        guide_7(command, replies)


def guide_6_other(replies):
    txt = f"***cannot specify port for protocol {gmc[5]}"
    dbot.commands.register(name="/b", func=guide_5)
    s = ""
    d = ""
    if gmc[6] == gmd[6]:
        dbot.commands.register(name="/s", func=guide_7)
        s = "\n🔺 /s  (skip)"
    else:
        dbot.commands.register(name="/d", func=guide_6_other_def)
        d = "\n🔺 /d  (default)"
        txt = f"{txt}\nuse /d to set ports to default (any) or /b to choose a different protocol"
    replies.add(
        f"🌐 GUIDE (7/8)\n{txt}\n\n{guide_r(6)}\n{d}\n🔺 /b  (back){s}\n🔺 /q  (quit)"
    )


def guide_6_other_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[6] = gmd[6]
    guide_7(command, replies)


def guide_7(command, replies):
    """."""
    if not verify(command.message):
        return
    txt = "Would you like to add a comment to this rule?\n\nThis setting is optional (Default: None), you may specify a comment using  // whateveryoulikeincludingspacesandsuch"
    guide_unreg()
    dbot.commands.register(name="/b", func=guide_6)
    dbot.commands.register(name="/s", func=guide_finish)
    dbot.commands.register(name="//", func=guide_7_pl)
    d = ""
    if gmc[7] != gmd[7]:
        dbot.commands.register(name="/d", func=guide_7_def)
        d = "\n🔺 /d  (default)"
    replies.add(
        f"🌐 GUIDE (8/8)\n{txt}\n\n{guide_r(7)}\n\n🔺 //  *comment*{d}\n🔺 /b  (back)\n🔺 /s  (skip)\n🔺 /q  (quit)"
    )


def guide_7_def(command, replies):
    """."""
    if not verify(command.message):
        return
    gmc[7] = gmd[7]
    guide_finish(command, replies)


def guide_7_pl(command, replies):
    """."""
    if not verify(command.message):
        return
    if not command.payload:
        replies.add("⚠️ expects comment")
        guide_7(command, replies)
    else:
        gmc[7] = command.payload
        guide_finish(command, replies)


def guide_finish(command, replies):
    """."""
    if not verify(command.message):
        return
    x = "add"
    if gmc[0] != gmd[0]:
        x = "insert"
    txt = f"Rule building is done.\nPlease check if the rule below matches your expectation, if so you may use /f  to {x} this rule and finish this guide."
    guide_unreg()
    dbot.commands.register(name="/b", func=guide_6)
    dbot.commands.register(name="/f", func=guide_exec)
    replies.add(
        f"🌐 GUIDE\n{txt}\n\n{guide_r(8)}\n\n🔺 /f  (finish)\n🔺 /b  (back)\n🔺 /q  (quit)"
    )


def guide_exec(command, replies):
    """."""
    if not verify(command.message):
        return
    clear_cmd()
    for c in ["b", "f", "q"]:
        with suppress(Exception):
            dbot.commands.unregister(name=f"/{c}")
    x = []
    if gmc[0] != gmd[0]:
        x.append("insert")
        x.append(gmc[0])
        ufwp.UFWParser().register_command(ufwp.UFWCommandRule("insert"))
    x.append(gmc[2])
    if gmc[1] != gmd[1]:
        x.append("out")
    if gmc[3] != gmd[3]:
        x.append("from")
        x.append(gmc[3])
    if gmc[4] != gmd[4]:
        x.append("to")
        x.append(gmc[4])
    if "from" in x or "to" in x:
        x.append("proto")
        if gmc[5] == "both":
            x.append("any")
        else:
            x.append(gmc[5])
        x.append("port")
        x.append(gmc[6])
    else:
        if gmc[5] != gmd[5] and gmc[6] != gmd[6]:
            x.append(f"{gmc[6]}/{gmc[5]}")
        elif gmc[5] == gmd[5] and gmc[6] != gmd[6]:
            x.append(gmd[6])
    ufwp.UFWParser().register_command(ufwp.UFWCommandRule(gmc[2]))
    if gmc[7] != gmd[7]:
        x.append("comment")
        x.append(gmc[7])
    try:
        pr = ufwp.UFWParser().parse_command(x)
        fw()[0].do_action(
            pr.action,
            pr.data.get("rule", ""),
            pr.data.get("iptype", ""),
            True,
        )
    except:
        replies.add(f"⛔️ ufw error ({x[0]})")
        guide_finish(command, replies)
        return
    x = []
    for c in fw()[1].get_rules():
        x.append(f"🔹 {len(x) + 1}:  {ufwp.UFWCommandRule.get_command(c)}")
    x = "\n".join(x)
    replies.add(f"🌐 RULES\n{x}")
    menu()


# >>> SCAN


def scan(command, replies):
    """."""
    if not verify(command.message):
        return
    replies.add(
        f"🌐 SCAN\nPlease check\nhttps://github.com/janekc/firewall-bot for version greater than {version}"
    )


# >>> TESTCODE / NOTES

# NOPE: support for named protocols -> rules will use the actual ports, user might not recognize
# NOPE: mark added/modified/inserted rule -> can't account for rule already existing and/or parsing/format changes
# NOPE: f-string alignment -> no monospaced font in chats
# NOPE: find better ufw man and set link -> no better manpage available

# TODO: descriptive texts for guided mode steps incl. possible values
# TODO: scan
# TODO: add ufw and python version to /info, add nmap info (installed, version)
# TODO: code optimization for service_set(), service() and others
# TODO: comments / docstrings

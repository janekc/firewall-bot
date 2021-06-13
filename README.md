# firewall-bot
A simple chatbot designed to configure your firewall using ufw *Uncomplicated Firewall* commands.

## step-by-step guide to run your first bot
We will use [deltabot](https://github.com/deltachat-bot/deltabot) as a chatbot framework.
The chat betweent client and chatbot is e2e encrypted with [autocrypt](https://autocrypt.org/).
To use the bot you will need an email address for the bot and a [Deltachat client](https://get.delta.chat/)

Caveat:
If the email address you plan on using for your bot belongs to a domain that does not host a mail server under that domain (e.g. botname@yourdomain but imap/smtp.yourhostersdomain), you need to make sure that the deltabot init routine can find a suitable autoconfig file.
Additionally this file has to be served using TLS encryption since the init routine will not use plain http to access the file.
You can use the supplied config-v1.1.xml file and adapt it to suit the domain your email address belongs to and then serve it at https://yourdomain/mail/config-v1.1.xml
The init routine will then pick up the needed information automatically and set itself up for that account.
Of course there are different ways to accomplish this (autoconfig/autodiscover/.well-known etc.) but deltabot init will try pretty much every possible way to setup the given email address

For using ufw with the python module [pyufw](https://github.com/5tingray/pyufw), you have to be root.
Here's the description from pyufw:
> *Your script will have to be run with root privilages. Upon importing the module the ufw security checks will start and you may see some warning messages. The following checks will commence:*
>  - *is setuid or setgid (for non-Linux systems)*
>  - *checks that script is owned by root*
>  - *checks that every component in absolute path are owned by root*
>  - *warn if script is group writable*
>  - *warn if part of script path is group writable*

There are (at least) 3 ways to your own firewall-bot:
1. You use the python installation that is included in your OS (must be at least version 3.9) and install all packages listed in the Pipfile onto that. This approach is not recommended.
2. You create a virtual environment (using venv, which is included in python version 3.8+ or any other means of creating virtual python environments) and install the required packages into the that virtual environment.
3. You follow this guide, which will make use of pipenv (and with it pyenv) to not only install the required python version (independent from your system python installation) into an environment solely used for the firewall-bot, but also install every required package.

```
$ sudo su
```
If you are installing for the first time it may be a good idea, to save your current iptables rules
```
$ iptables-save > /root/iptables-backup
$ iptables-legacy-save > /root/iptables-backup-legacy
```
You can later reapply them with
```
$ iptables-restore /root/iptables-backup
$ iptables-restore /root/iptables-backup-legacy
```
Let's clone this repository
```
$ cd ~/git
$ git clone https://github.com/janekc/firewall-bot
$ cd firewall-bot
```
And use an pipenv which will help you not to litter your common python installation.
```
$ pipenv install
$ pipenv shell
```
Install the current uf master branch
```
$ cd ~/git
$ git clone -b master https://git.launchpad.net/ufw
$ cd ufw
$ pip install .
$ pip install deltachat
$ pip install deltabot
$ cd firewall-bot
```
Now let's initialize the bot with an email address
```
$ deltabot init <email address> <password>
```
The bot should be ready to use by now, let's see if it works!
```
$ deltabot serve
```
If it does, you can add the firewall module
```
$ deltabot add-module bot.py
$ deltabot serve
```
Post-Installation (as root/sudo):  
Make sure that no matter how restrictive your firewall-settings may be, the firewall-bot will always be able to fetch emails:
Insert the following lines into /etc/ufw/before.rules
```
# FWBOT
-A ufw-before-output -p tcp --dport 993 -j ACCEPT
-A ufw-before-output -p tcp --dport 465 -j ACCEPT
-A ufw-before-output -p udp --dport 53 -j ACCEPT
```
Additionally, if you want to make sure you always have SSH access, add this line ($PORT being the port you have set in your sshd config)
```
# SSHACCESS
-A ufw-before-input -p tcp --dport $PORT -j ACCEPT
```
Have the firewall-bot run as a system service:
- Move into your firewall-bot directory and activate the projects python environment:
```
$ cd *yourprojectdirectory*/firewall-bot
$ pipenv shell
```
- Display the path to the deltabot installation:
```
$ which deltabot
```
The output should look sth like this: /root/.local/share/virtualenvs/firewall-bot-DJhpAnUw/bin/deltabot.
You will need this full path to put in your service file. Exit the python environment to continue.
- Create a service file:
```
$ vi /etc/systemd/system/fwbot.service
```
- Insert the following into the service file:
```
[Unit]
Description=DeltaChatFirewallBot

[Service]
Type=simple
ExecStart=*your-path-to-deltabot* serve
Environment=PYTHONUNBUFFERED=1
SyslogIdentifier=fwbot

[Install]
WantedBy=multi-user.target
```
- After every change to service files do:
```
$ systemctl daemon-reload
```
Now you can use systemctl start/stop/status/enable/disable/restart/... fwbot.service like any other service.
At this point all "output" (stdout, stderr, print-statements) will be redirected by systemctl to syslog (/var/log/syslog).
You may want to change this behaviour:
- Open the syslog config
```
$ vi /etc/rsyslog.d/50-default.conf
```
- Insert the following into the config:
```
:programname,isequal,"fwbot"  /var/log/fwbot.log
```
- Restart the rsyslog daemon:
```
$ systemctl restart rsyslog
```
For the cherry on top, setup logrotation for fwbot-logging:
- Create a logrotate file:
```
$ vi /etc/logrotate.d/fwbot
```
- Insert the following into the logrotate file (daily zipping and max 5 logs - feel free to adapt this to your liking):
```
/var/log/fwbot.log {
    su root syslog
    daily
    rotate 5
    compress
    delaycompress
    missingok
    postrotate
        systemctl restart rsyslog > /dev/null
    endscript
}
```
- Run the rotation dry to make sure there are no errors:
```
$ logrotate --d /etc/logrotate.d/fwbot
```
- Run the rotation once:
```
$ logrotate --force /etc/logrotate.d/fwbot
```

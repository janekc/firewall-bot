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

# firewall-bot
A simple chatbot desinged to configre your firewall using ufw *Uncomplicated Firewall* commands.

## step-by-step guide to run your first bot
We will use [deltabot](https://github.com/deltachat-bot/deltabot) as a chatbot framework.
The chat betweent client and chatbot is e2e encrypted with [autocrypt](https://autocrypt.org/).
To use the bot you will need an email address for the bot and a [Deltachat client](https://get.delta.chat/)

For using ufw with the python module [pyufw](https://github.com/5tingray/pyufw), you have to be root.
Here's the description from pyufw:
> *Your script will have to be run with root privilages. Upon importing the module the ufw security checks will start and you may see some warning messages. The following checks will commence:*
>  - *is setuid or setgid (for non-Linux systems)*
>  - *checks that script is owned by root*
>  - *checks that every component in absolute path are owned by root*
>  - *warn if script is group writable*
>  - *warn if part of script path is group writable*
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

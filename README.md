# firewall-bot
Deltabot firewall Chatbot

## step-by-step guide to run your first bot
We will use (deltabot)[https://github.com/deltachat-bot/deltabot] as a chatbot framework.
Let's see how to get one running.

First let's clone the deltabot repository
```
$ cd git
$ git clone https://github.com/deltachat-bot/deltabot.git
```
Then create a new venv for our bot and install deltabot
```
$ mkdir ~/firewallbot
$ cd firewallbot
$ python3 -m venv ./
$ source bin/activate
$ pip3 install deltabot
```
If that doesn't work you can try to install the deltachat python package by compiling the rust bindings in (deltachat-core-rust)[https://github.com/deltachat/deltachat-core-rust/tree/master/python]

Now let's create a temporary email address
```
$ curl -X POST https://testrun.org/new_email\?t\=1w_96myYfKq1BGjb2Yc\&n\=oneweek
```
You will get bach something like this `"email":"tmp.hjhjdh@testrun.org","expiry":"1w","password":"kjsgfksuhfoe","ttl":604800`

Now let's tell the bot to use this email address
```
$ deltabot init tmp.hjhjdh@testrun.org kjsgfksuhfoe
```
The bot should be ready to use by now, but let's clone this repository and register the example code!
```
$ git clone https://github.com/janekc/firewall-bot.git
$ cd firewall-bot
```
Now let's register our plugin to the bot
```
$ deltabot add-module ./src
```
And run it
```
$ deltabot serve
```
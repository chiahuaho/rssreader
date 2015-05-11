Introduction
============

*rssreader* is a small project with the most basic utilities to read the RSS feeds
in a text-based environment.

This project is also an experimental environment for studying bandit problems
and recommender systems.


Install
=======

Please add the directory of rssreader to the system path, and rssreadercore.py 
to the Python path. Alternatively, please run ./rssreader in the directory of
the package.

System Requirement
------------------

This tool is only for Linux environments with latest Python.

Required Libraries
------------------

- Python 2.7+ (including sqlite3 package).
  *Python 3+ is not supported.*
- Python NLTK package (debian: python-nltk)
- Python LIBLINEAR package (debian: python-liblinear)


Usage
=====

- Add an RSS:

  rssreader add https://github.com/ho-chiahua.atom

- Show all feeds:

  rssreader ls

- Show new feeds:

  rssreader ls -n

- Read the details of a feed:

  rssreader read tag:github.com,2008:CreateEvent/2790427132

- Recommend new feeds:

  rssreader ls -n -r

- More usages for ls

  rssreader ls -h


Recommender
===========

The built-in recommender is a very simple classifier based on bi-grams of the
feed title. To modify the recommender, the most easy approach is to modify the
Recommender class in rssreadercore.py. Making the recommender easier to be
replaced by users' plug-ins is a future work.


Console
=======

*rssconsole* is a simple console. After running the console, users do not need
to type the program name. For example, they can directly type "ls" to list 
feeds.

rssconsole>> ls

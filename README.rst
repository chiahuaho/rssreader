Introduction
============

*RSSREADER* is a small project with the most basic utilities to read the RSS 
feeds in a text-based environment.

This project is also an experimental environment for studying bandit problems
and recommender systems.


Installation
============

Please add the directory of rssreader and rssconsole to the system path, and put
rssreadercore.py to the Python path. Alternatively, please run ./rssreader in 
the directory of the package.

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

- Add an RSS::
  
  $> rssreader add https://github.com/chiahuaho.atom

- Show all feeds::
  
  $> rssreader ls

- Show new feeds::
  
  $> rssreader ls -n

- Read the details of a feed::
  
  $> rssreader read tag:github.com,2008:CreateEvent/2790427132

- Recommend new feeds::
  
  $> rssreader ls -n -r

- More usages for ls::
  
  $> rssreader ls -h


Recommender
===========

The built-in recommender is a very simple classifier based on bi-grams of the
feed title. To modify the recommender, the most easy approach is to modify the
Recommender class in rssreadercore.py. Making the recommender easier to be
replaced by users' plug-ins is a future work.


Console
=======

*rssconsole* is a simple console to use rssreader. After running the console, 
users do not need to type the program name (i.e., "rssreader"). For example, 
users can directly type "ls" to list feeds::
        $> rssconsole
        rssconsole>> add  https://github.com/chiahuaho.atom
        rssconsole>> ls -l 5

"""
 Scrapy settings for scraper project

 For simplicity, this file contains only settings considered important or
 commonly used. You can find more settings consulting the documentation:

     https://docs.scrapy.org/en/latest/topics/settings.html
     https://docs.scrapy.org/en/latest/topics/downloader-middleware.html
     https://docs.scrapy.org/en/latest/topics/spider-middleware.html
"""

BOT_NAME = 'scrapy_athlinks'

SPIDER_MODULES = ['scrapy_athlinks.spiders']
NEWSPIDER_MODULE = 'scrapy_athlinks.spiders'

# Obey robots.txt rules
ROBOTSTXT_OBEY = False

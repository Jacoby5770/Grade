# -*- coding: utf-8 -*-
import scrapy, re
from scrapy_splash import SplashRequest
from GradeScraper.items import GradeData

class GradesSpider(scrapy.Spider):
    name = 'grades'
    custom_settings = {
        'SPLASH_URL': 'http://192.168.99.100:8050/',
        'DOWNLOADER_MIDDLEWARES': {
            'scrapy_splash.SplashCookiesMiddleware': 723,
            'scrapy_splash.SplashMiddleware': 725,
            'scrapy.downloadermiddlewares.httpcompression.HttpCompressionMiddleware': 810,
        },
        'SPIDER_MIDDLEWARES': {
            'scrapy_splash.SplashDeduplicateArgsMiddleware': 100,
        },
        'DUPEFILTER_CLASS': 'scrapy_splash.SplashAwareDupeFilter',
    }

    def __init__(self, username='default', password='default'):
        self.baseURL = 'https://brightspace.vanderbilt.edu'
        self.username = username
        self.password = password
        print(username, password)
        self.renderPage = """
        funcion main(splash, args)
            assert(splash:go(args.url))
            assert(splash:wait(3))
            return {
                html = splash:html(),
            }
        """
        self.expandGrades = """
        function main(splash, args)
            assert(splash:go(args.url))
            assert(splash:wait(3))
            assert(splash:runjs('document.querySelector("div.d2l-collapsepane-header.d2l_1_59_890.d2l_1_60_709.d2l-collapsepane-collapsed").click()'))
            assert(splash:wait(1))
            return {
                html = splash:html(),
            }
        """

    def start_requests(self):
        script = """
        function main(splash, args)
            assert(splash:go(args.url))
            assert(splash:wait(3))
            assert(splash:runjs('document.getElementById("username").value = "zhanc24"; document.getElementById("password").value = "Jodie2000!"; setTimeout(postOk(), 1000);'))
            assert(splash:wait(12))
            return {
                html = splash:html(),
            }
        end
        """#.format(self.username, self.password)
        yield scrapy.Request(
            url = r'https://sso.vanderbilt.edu/idp/SSO.saml2?SAMLRequest=jdE7a8MwEADgvdD%2fYLTbsmT5JexAaJdAuiRthy5FlpTEIEuuTg79%2bVUaQjN2uwcH39116yWc7E5%2fLRpCsnnuEYjJ%2bGv%2bWdG6VmpgbVNJRg%2b0FTkhJVFlJVjZFAIl79rD6GyPaJajZAOw6I2FIGyIpZw0KSEprV7zktOc50XWFnVJCf1AyRpA%2bxBnn5yFZdJ%2br%2f15lPptt%2b3RKYQZOMaDH4%2bnALOQOjsLq7QfRhMyrRasqMFmxiL6sXHH0eKLfHuJsthDyfdkLPRo8ZY7ASNwKyYNPEi%2bX79seQTz2bvgpDNo9fiQJN0v3%2f9nUNzwaHWjFodStod6SKtmKFOmKp22RLCUtpKxIVcVYU0WtI2ngex%2bL%2bmmP3qHr4gI6vD9b1Y%2f&RelayState=%2fd2l%2fhome',
            callback = self.parseHome,
            meta = {
                'splash': {
                    'args': {'lua_source': script},
                    'endpoint': 'execute',
                }
            }
        )

    def parseHome(self, response):
        classLinks = response.css('d2l-tab-panel[aria-label="2018 Fall"] div.my-courses-content.style-scope.d2l-my-courses-content a.d2l-focusable.style-scope.d2l-card::attr(href)')
        for href in classLinks:
            yield scrapy.Request(
                url = self.baseURL+href.extract(), 
                callback = self.parseClassLink,
                meta = {
                    'splash': {
                        'args': {'lua_source': self.renderPage},
                        'endpoint': 'execute',
                    }
                }
            )

    def parseClassLink(self, response):
        gradeLink = response.xpath('//a[@class="d2l-navigation-s-link" and text()="Grades"]/@href').extract()
        if gradeLink:
            return scrapy.Request(
                url = self.baseURL+gradeLink, 
                callback = self.parseGrades,
                meta = {
                    'splash': {
                        'args': {'lua_source': self.renderPage},
                        'endpoint': 'execute',
                    }
                }
            )
        else:
            classProgressLink = response.xpath('//a[@class="d2l-navigation-s-link" and text()="Class Progress"]/@href').extract()
            if classProgressLink:
                return scrapy.Request(
                    url = self.baseURL+classProgressLink, 
                    callback = self.parseClassProgress,
                    meta = {
                        'splash': {
                            'args': {'lua_source': self.expandGrades},
                            'endpoint': 'execute',
                        }
                    }
                )

    def parseGrades(self, response):
        data = GradeData()
        data['assignments'] = dict()
        className = response.css('div.d2l-navigation-s-title-container a.d2l-navigation-s-link::text').extract()
        data['assignments']['class'] = className
        for asgn, grade in zip_longest(response.css('th.d_gt.d_ich.d2l-table-cell-first label::text'), 
                                       response.css('td.d_gn.d_gr.d_gt.d2l-table-cell-last label::text')):
            data['assignments'][asgn.extract()] = {'grade': grade.extract(), 'achieved': None, 'total': None}
        return data

    def parseClassProgress(self, response):=
        data = GradeData()
        data['assignments'] = dict()
        className = response.css('div.d2l-navigation-s-title-container a.d2l-navigation-s-link::text').extract()
        data['assignments']['class'] = className
        for asgn, grade, percentStr in zip_longest(response.css('h4.d2l-heading.vui-heading-3.d2l-heading-none.d2l_2_9_601::text'), 
                                                   response.css('div.d2l_2_11_476 span.d2l-textblock.d2l-textblock-strong::text'), 
                                                   response.css('div.d2l-textblock.js_Weight.d2l_2_8_609.d2l_2_23_144.d2l_2_24_900::text')):
            percentages = re.findall(r'[0-9]+\.?[0-9]+', percentStr.extract())
            achieved = total = None
            if len(percentages) == 2:
                total, achieved = percentages
            data['assignments'][asgn.extract()] = {'grade': grade.extract(), 'achieved': achieved, 'total': total}
        return data

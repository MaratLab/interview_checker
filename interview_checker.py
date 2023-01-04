from ctypes import Union
import sys
import os
import time
import logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

import telegram
from getpass import getpass
from telegram import Update
from telegram import Bot
from telegram.ext import ApplicationBuilder, ContextTypes, CommandHandler
import asyncio

from selenium import webdriver
from selenium.webdriver.chrome.options import Options as COptions
from selenium.webdriver.firefox.options import Options as FOptions
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.wait import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.action_chains import ActionChains

import threading
import random
import datetime
import pytz

BOTTOKEN = "TOKEN"
BOTCHATIDS = {"Name" : 1234567890}
BOTRUN = False
BOTTHREAD = None

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == BOTCHATIDS["Name"]:
        # print(update.effective_chat.username)
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="I'm a bot, I am started!"
        )
        context.job_queue.run_once(bot_check_timetable_periodically, 5, chat_id=update.effective_chat.id, name=str(update.effective_chat.id), data=None)

async def stop(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == BOTCHATIDS["Name"]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Schedule jobs for removal."
        )
        for job in context.job_queue.jobs():
            job.schedule_removal()

async def check(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == BOTCHATIDS["Name"]:
        await context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Checking..."
        )
        context.job_queue.run_once(bot_check_timetable_once, 5, chat_id=update.effective_chat.id, name=str(update.effective_chat.id), data=None)

async def screenshot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == BOTCHATIDS["Name"]:
        print(update.effective_chat.username)
        await context.bot.send_photo(
            photo=open("ss.png", "rb"),
            chat_id=update.effective_chat.id,
            caption=str(datetime.datetime.fromtimestamp(os.path.getmtime("ss.png"), datetime.timezone.utc).astimezone(pytz.country_timezones.get("Europe/Moscow")).strftime('%Y-%m-%d %H:%M:%S'))
        )

async def error(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.id == BOTCHATIDS["Name"]:
        print(update.effective_chat.username)
        await context.bot.send_photo(
            photo=open("error.png", "rb"),
            chat_id=update.effective_chat.id,
            caption=str(datetime.datetime.fromtimestamp(os.path.getmtime("error.png"), datetime.timezone.utc).astimezone(pytz.country_timezones.get("Europe/Moscow")).strftime('%Y-%m-%d %H:%M:%S'))
        )

def launch_bot():
    application = ApplicationBuilder().token(BOTTOKEN).build()
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('stop', stop))
    application.add_handler(CommandHandler('screenshot', screenshot))
    application.add_handler(CommandHandler('error', error))
    application.add_handler(CommandHandler('check', check))
    application.run_polling()

async def bot_send_time(context: ContextTypes.DEFAULT_TYPE):
    await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=str(datetime.datetime.now())
        )
    context.job_queue.run_once(bot_send_time, random.randint(1,2)*5, chat_id=context.job.chat_id, name=str(context.job.chat_id), data=None)

async def bot_check_timetable_once(context: ContextTypes.DEFAULT_TYPE):
    answer = check_dates()
    await context.bot.send_message(
            chat_id=context.job.chat_id,
            text=str(answer)
        )

async def bot_check_timetable_periodically(context: ContextTypes.DEFAULT_TYPE):
    answer = check_dates()
    if answer != "В настоящее время нет свободных мест для записи":
        await context.bot.send_message(
                chat_id=context.job.chat_id,
                text=str(answer)
            )
    context.job_queue.run_once(bot_check_timetable_periodically, 4*60*60 + random.randint(10,20)*60, chat_id=context.job.chat_id, name=str(context.job.chat_id), data=None)

def get_browser_driver(browser: str ="Chrome") -> webdriver.Firefox | webdriver.Chrome:
    if browser == "Chrome":
        options = COptions()
        options.add_argument("--incognito")
    else:
        options = FOptions()
        options.add_argument("-private")
    options.add_argument("--headless")
    user_agent = 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/60.0.3112.50 Safari/537.36'    
    options.add_argument('user-agent={0}'.format(user_agent))

    if browser == "Chrome":
        driver = webdriver.Chrome(executable_path="./chromedriver.exe", options=options)
    else:
        driver = webdriver.Firefox(executable_path="./geckodriver.exe", options=options)
    driver.set_window_size(1920,1080)
    # driver.maximize_window()
    return driver

def error_handler(driver):
    driver.save_screenshot("error.png")
    driver.quit()
    # sys.exit()

def check_dates_wait_overlay(driver):
    try:
        waiter = WebDriverWait(driver, 15).until(
            EC.none_of(EC.presence_of_element_located((By.CLASS_NAME, "ngx-overlay foreground-closing"))))
    except TimeoutException:
        error_handler(driver)

def check_dates():
    driver = get_browser_driver("Chrome")
    # driver = get_browser_driver("Firefox")
    driver.implicitly_wait(8)
    driver.get("https://visa.vfsglobal.com/rus/ru/aut/login")
    
    actions = ActionChains(driver)

    check_dates_wait_overlay(driver)
    
    try:
        waiter = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located( (By.ID, "onetrust-accept-btn-handler")))
        print("Accept cookies clickable")
    except TimeoutException:
        print("Accept cookies timeout...")
        error_handler(driver)
        return "Error: Accept cookies timeout..."
    
    button = driver.find_element(By.ID, "onetrust-accept-btn-handler")
    actions.move_to_element(button).click(button).perform()
    
    try:
        waiter = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "//span[text()=' Войти ']")))
        print("Loaded login form")
    except TimeoutException:
        print("Load login form timeout...")
        error_handler(driver)
        return "Error: Load login form timeout..."
    
    login_form = driver.find_element(By.ID, "mat-input-0")
    password_form = driver.find_element(By.ID, "mat-input-1")
    login_form.send_keys("email@yandex.ru")
    password_form.send_keys("password")
    button = driver.find_element(By.XPATH, "//span[text()=' Войти ']")
    actions.move_to_element(button).click(button).perform()

    try:
        waiter = WebDriverWait(driver, 30).until(
            # EC.element_to_be_clickable((By.XPATH, "(//span[text()=' Записаться на прием '])[2]")))
            EC.url_to_be("https://visa.vfsglobal.com/rus/ru/aut/dashboard"))
        print("Dashboard loaded")
    except TimeoutException:
        print("Dashboard timeout...")
        error_handler(driver)
        return "Error: Dashboard timeout..."

    check_dates_wait_overlay(driver)
    
    try:
        waiter = WebDriverWait(driver, 30).until(
            EC.element_to_be_clickable((By.XPATH, "(//span[text()=' Записаться на прием '])[2]")))
            # EC.url_to_be("https://visa.vfsglobal.com/kaz/ru/aut/dashboard"))
        print("Schedule field 1")
    except TimeoutException:
        print("Schedule field 1 timeout...")
        error_handler(driver)
        return "Error: Schedule field 1 timeout..."
        
    button = driver.find_element(By.XPATH, "(//span[text()=' Записаться на прием '])[2]")
    actions.move_to_element(button).click(button).perform()

    try:
        # button = driver.find_elements(By.XPATH, "//span[text()=' Записаться на прием ']")[1]
        waiter = WebDriverWait(driver, 30).until(
            EC.url_to_be("https://visa.vfsglobal.com/rus/ru/aut/application-detail"))
        print("Application detail loaded")
    except TimeoutException:
        print("Application detail timeout...")
        error_handler(driver)
        return "Error: Application detail timeout..."

    check_dates_wait_overlay(driver)

    try:
        waiter = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "(//mat-select)[1]")))
        print("Dashboard loaded")
    except TimeoutException:
        print("Dashboard timeout...")
        error_handler(driver)
        return "Error: timeout"

    button = driver.find_element(By.XPATH, "(//mat-select)[1]")
    actions.move_to_element(button).click(button).perform()

    check_dates_wait_overlay(driver)

    try:
        waiter = WebDriverWait(driver, 10).until(
            EC.element_to_be_clickable((By.XPATH, "(//span[text()=' Austria Visa Application Center Moscow '])")))
        print("Dashboard loaded")
    except TimeoutException:
        print("Dashboard timeout...")
        error_handler(driver)
        return "Error: timeout"

    button = driver.find_element(By.XPATH, "(//span[text()=' Austria Visa Application Center Moscow '])")
    actions.move_to_element(button).click(button).perform()

    check_dates_wait_overlay(driver)
    
    # try:
    #     waiter = WebDriverWait(driver, 10).until(
    #         EC.element_to_be_clickable((By.XPATH, "(//mat-select)[3]")))
    #     print("Dashboard loaded")
    # except TimeoutException:
    #     print("Dashboard timeout...")
    #     error_handler(driver)
    #     return "Error: timeout"

    # button = driver.find_element(By.XPATH, "(//mat-select)[3]")
    # actions.move_to_element(button).click(button).perform()

    # check_dates_wait_overlay(driver)

    # try:
    #     waiter = WebDriverWait(driver, 10).until(
    #         EC.element_to_be_clickable((By.XPATH, "(//span[text()=' Tourist '])")))
    #     print("Dashboard loaded")
    # except TimeoutException:
    #     print("Dashboard timeout...")
    #     error_handler(driver)
    #     return "Error: timeout"

    # button = driver.find_element(By.XPATH, "(//span[text()=' Tourist '])")
    # actions.move_to_element(button).click(button).perform()

    check_dates_wait_overlay(driver)

    time.sleep(1)

    driver.save_screenshot("ss.png")

    try:
        waiter = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "(//div[text()=' В настоящее время нет свободных мест для записи '])")))
        print("No slots")
        answer = "В настоящее время нет свободных мест для записи"
        driver.quit()
        return answer
    except TimeoutException:
        print("Possible slots")
    
    try:
        waiter = WebDriverWait(driver, 30).until(
            EC.visibility_of_element_located((By.XPATH, "(//div[starts-with(text(), ' Самый')])")))
        print("Earliest slot available")
        earliest_time_text = driver.find_element(By.XPATH, "(//div[starts-with(text(), ' Самый')])").get_attribute("textContent")
        answer = earliest_time_text
        print(earliest_time_text)
        driver.quit()
        return answer
    except TimeoutException:
        print("Earliest slot not available")
        error_handler(driver)
        answer = "Earliest slot not available"
        driver.quit()
        return answer


def load_yandex():
    driver = get_browser_driver("Chrome")
    # driver = get_browser_driver("Firefox")
    driver.implicitly_wait(5)
    driver.get("https://ya.ru")
    try:
        waiter = WebDriverWait(driver, 30).until(
            EC.url_to_be("https://ya.ru"))
        print("Yandex loaded")
    except TimeoutException:
        print("Yandex timeout...")
        error_handler(driver)


if __name__ == "__main__":
    # Password = getpass()
    launch_bot()
    # load_yandex()
    
    # check_dates()

    # sys.exit()

from selenium import webdriver

################ Web driver defination #####################
####### If failed, please fix it by users themselves #######
binPath = "chromium/ungoogled-chromium-portable.exe"
driverPath = "chromium/chromedriver.exe"

from selenium.webdriver.chrome.service import Service
service = Service(executable_path=driverPath)
from selenium.webdriver.chrome.options import Options
options = Options()
options.binary_location = binPath

browser = webdriver.Chrome(service=service, options=options)
############################################################

browser.get("https://www.bilibili.com")
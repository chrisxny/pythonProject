from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import time

executable_path= "/webdriver/chromedriver.exe"
house_address="6153 Marsh Trail Dr, Odessa, FL 33556"
property_search_website="https://hillsborough.county-taxes.com/public/search/property_tax?action_location=Landing+Page"


driver = webdriver.Chrome(executable_path)
driver.get(property_search_website)
search_box = driver.find_element(By.ID, "search_query")
search_box.send_keys(house_address)
search_button=driver.find_element(By.XPATH, "/html/body/div[2]/div[2]/div/main/section/div[1]/form/div/div/div[2]/button").click()
time.sleep(2)
property_page = driver.current_window_handle
title_name = driver.find_element(By.XPATH, "//*[@class=' container result property_tax']/div[1]/div/a").click()
appr_link = driver.find_element(By.XPATH,"/html/body/div[2]/div[2]/div/main/section/div[2]/div[2]/div[3]/div[3]/a").click()
driver.switch_to.window(driver.window_handles[1])
beds_num=driver.find_element(By.XPATH,"/html/body/form/div[5]/div/div/div/div/div/div/div[3]/div[6]/div[6]/div[3]/table[2]/tbody/tr[12]/td[2]").text
baths_num=driver.find_element(By.XPATH,"/html/body/form/div[5]/div/div/div/div/div/div/div[3]/div[6]/div[6]/div[3]/table[2]/tbody/tr[13]/td[2]").text
print(beds_num)
driver.switch_to.window(property_page)
driver.find_element(By.XPATH, "/html/body/div[2]/header/div/section/div[2]/div/div/div[2]/div/a/h2/div[2]").click()
# element.close()
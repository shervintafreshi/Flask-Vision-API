
import io
import os
import re
import cv2
import time
import pytesseract
import pandas as pd
import numpy as np
import concurrent.futures
from pytesseract import Output
from googlemaps import Client as client
from google.cloud import vision
from PIL import Image

######### Google Cloud Credentilas #########

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'./btr490-project-firebase-adminsdk-3xbj4-61e9e79cb7.json'


######### Required Image processing Functions ##############

#get grayscale 
def get_grayscale(image):
    return cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

#get inverse grascale
def get_inverse_grayscale(image):
    return cv2.bitwise_not(image)

#noise removal
def remove_noise(image):
    return cv2.medianBlur(image,5)
 
#thresholding
def thresholding(image):
    return cv2.threshold(image, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)[1]

##Adaptive Gaussian Thresholding
def Adaptive_thresholding(image):
    return cv2.adaptiveThreshold(image, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,cv2.THRESH_BINARY,11,2)    

#dilation
def dilate(image):
    kernel = np.ones((5,5),np.uint8)
    return cv2.dilate(image, kernel, iterations = 1)
    
#erosion
def erode(image):
    kernel = np.ones((5,5),np.uint8)
    return cv2.erode(image, kernel, iterations = 1)

#opening - erosion followed by dilation
def opening(image):
    kernel = np.ones((5,5),np.uint8)
    return cv2.morphologyEx(image, cv2.MORPH_OPEN, kernel)

#canny edge detection
def canny(image):
    return cv2.Canny(image, 100, 200)

#Median Blur
def blur_median(image):
    return cv2.medianBlur()

#Gaussian Blurring
def blur_gaussian(image):
    return cv2.GaussianBlur(image,(5,5),0)

#Bilateral Filtering
def Bilateral(image):
    return cv2.BilateralFilter(img,9,75,75)

#skew correction
def deskew(image):
    coords = np.column_stack(np.where(image > 0))
    angle = cv2.minAreaRect(coords)[-1]
    if angle < -45:
        angle = -(90 + angle)
    else:
        angle = -angle
    (h, w) = image.shape[:2]
    center = (w // 2, h // 2)
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    rotated = cv2.warpAffine(image, M, (w, h), flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    return rotated

#template matching
def match_template(image, template):
    return cv2.matchTemplate(image, template, cv2.TM_CCOEFF_NORMED) 

############## Image Conversion Assistant Class ##############

class Extractor():
  
  __API_KEY = 'AIzaSyDSN-u7kK05H45CZLTnl6h9vFnCy9EMxnw' 
  __JSON_PATH = './json_documents'
  __IMAGE_PATH = './test_images' 
  __UF_DATA_PATH = './extraction_data'

  def __init__(self):
       
     Extractor.__data_DICT = {}
     Extractor.__custom_config = r'--oem 3 --psm 6 outputbase digits'

  def __is_number(n):
     try:
         float(n)   
     except ValueError:
         return False
     return True

  def get_resultant(self): 
     return Extractor.__data_DICT             

  def start_EXTRACTION(self):
      # Multiprocessing
     img_ID_LIST = os.listdir(Extractor.__IMAGE_PATH)[:]
     Extractor.__extraction_ROUTINE(img_ID_LIST[1])
     #with concurrent.futures.ThreadPoolExecutor() as executor:
        #extracton_STATUS_LIST = executor.map(Extractor.__extraction_ROUTINE, img_ID_LIST)
     
  def __extraction_ROUTINE(img_ID):

    # Run Tesseract OCR Data Extraction Method  
    i = 10
    while True:
       Extractor.__OCR_ROUTINE_DEFAULT(img_ID, 100 + i)
  
       if Extractor.__extract_DATA(img_ID) is not False: 
            return None
       elif i < 20:
            i += 10
       elif i == 20:
            break

    # Run GCP Cloud Vision Data Extraction Method
    Extractor.__OCR_ROUTINE_GCP_VISION(img_ID)
    if Extractor.__extract_DATA_GCP(img_ID) is not False:
        return None

    Extractor.__data_DICT[img_ID[:-4]] = None            
      
  def __extract_DATA(img_test_ID):
       
     total_cost_LC = None
     tax_amount_LC = None
     purchase_date_LC = None
     business_name_LC = None
     category_LC = None
     query_info_LC = []
     
     data_path = "./extraction_data/" + img_test_ID + "_RTD.txt"

     text_data = open(data_path, 'r')
     data_lines = text_data.readlines()  
     

     for line in data_lines: 

        # Extract Receipt Cost
        match_Total = re.search(r'\bTotal\b', line) or re.search(r'\bTOTAL\b', line) or re.search(r'Sub w/Tax:', line)
        if (match_Total != None and total_cost_LC == None and len(line.split()) > 1):                                                    
            for word in line.split():
                if (line.split()[0] == 'Sub' and line.split()[1] == 'Total:'):
                   break
                if word.startswith('$') and Extractor.__is_number(word[1:]): 
                   total_cost_LC = float(word[1:])
                elif Extractor.__is_number(word):
                   total_cost_LC = float(word)   

        #Extract Tax Amount
        match_Tax = re.search(r'\bTax\b', line) or re.search(r'\bTAX\b', line) or re.search(r'Tax::', line)
        if (match_Tax != None and tax_amount_LC == None and len(line.split()) > 1):                                                
            for word in line.split():
                if word.startswith('$') and Extractor.__is_number(word[1:]):
                   tax_amount_LC = float(word[1:])
                elif Extractor.__is_number(word):
                   tax_amount_LC = float(word)

        #Extract Date of Purchase
        match_Date = re.search(r'\b(1[0-2]|0[1-9])-(3[01]|[12][0-9]|0[1-9])-[0-9]{4}\b', line) or re.search(r'\b(1[0-2]|0[1-9])[/-](3[01]|[12][0-9]|0[1-9])[/-][0-9]{2}\b', line)
        if (match_Date != None and purchase_date_LC == None):                                                               
            for word in line.split():
                if (re.match(r'\b(1[0-2]|0[1-9])-(3[01]|[12][0-9]|0[1-9])-[0-9]{4}\b', word)):
                   purchase_date_LC = word
            for word in line.split():  
                if (re.match(r'\b(1[0-2]|0[1-9])[/-](3[01]|[12][0-9]|0[1-9])[/-][0-9]{2}\b', word)):
                   purchase_date_LC = word        

        #Extract Business Phone Number
        Match_Phone = re.search(r'\b\d{3}-\d{3}-\d{4}\b', line) or re.search(r'[(]\d{3}[)][ ]\d{3}-\d{4}', line)
        if (Match_Phone != None and query_info_LC == []):  
            for word in line.split():
                if (re.match(r'\b\d{3}-\d{3}-\d{4}\b', word)):
                   query_info_LC = Extractor.__query_INFO(word)[:]
            if (query_info_LC == []):
                match_obj =  re.search(r'[(]\d{3}[)][ ]\d{3}[-]\d{4}', line)
                phone_number = match_obj.group(0)   
                query_info_LC = Extractor.__query_INFO(phone_number)[:]

     if total_cost_LC == None or tax_amount_LC == None or len(query_info_LC) == 0:
         return False
     else:
         if (purchase_date_LC == None):
              purchase_date_LC = '00/00/0000'
         elif (len(purchase_date_LC) == 8):
              purchase_date_LC = purchase_date_LC[:6] + '20' + purchase_date_LC[6:]      
         
         business_name_LC = query_info_LC[0]
         category_LC = query_info_LC[1]

         Extractor.__data_DICT[img_test_ID[:-4]] = [
             purchase_date_LC, 
             business_name_LC,
             category_LC,
             tax_amount_LC,
             total_cost_LC,
            ]
         return True

  def __extract_DATA_GCP(img_test_ID):

     total_cost_LC = None
     tax_amount_LC = None
     purchase_date_LC = None
     business_name_LC = None
     category_LC = None
     query_info_LC = []
     
     data_path = "./extraction_data/cloud-vision-output.txt" 

     text_data = open(data_path, 'r')
     data_lines = text_data.readlines()  
     

     Line_Number = 0
     Line_Data = []

     #Store each line into Array List
     for line in data_lines:
        Line_Data.append(line)


     for line in data_lines:

        #Extract Receipt Cost
        match_Total = re.search(r'Total', line) or re.search(r'TOTAL', line) or re.search(r'Sub w/Tax:', line) or re.search(r'Total:', line)
        if (match_Total != None and total_cost_LC == None and len(line.split()) >= 1):

               
            for word in line.split():            
                if (line.split()[0] == 'Sub' and line.split()[1] == 'Total:'):
                   break
                if (line.split()[0] == 'Total' and line.split()[1] == 'Tax:'):
                   break
                 
                if ( Extractor.__is_number(Line_Data[Line_Number - 1][1:]) and Extractor.__is_number(Line_Data[Line_Number + 1][1:]) ):
                   total_cost_LC = float(Line_Data[Line_Number + 1][1:])
                   break

        #Extract Tax Amount
        match_Tax = re.search(r'Tax', line) or re.search(r'TAX', line) or re.search(r'Tax::', line) or re.search(r'Total Tax:', line)
        if (match_Tax != None and tax_amount_LC == None and len(line.split()) >= 1):


            for word in line.split():

                Found_Number = False
                i = 1

                while(Found_Number is not True):
                    if (Extractor.__is_number(Line_Data[Line_Number - i][1:])):
                        tax_amount_LC = float(Line_Data[Line_Number + i][1:])
                        break
                    else:
                        i += 1    
                
                if (word.startswith('$') and Extractor.__is_number(word[1:])):
                   tax_amount_LC = float(word[1:])
                   break
                elif Extractor.__is_number(word):
                   tax_amount_LC = float(word)
                   break            
        
         
        #Extract Business Phone Number
        Match_Phone = re.search(r'\b\d{3}-\d{3}-\d{4}\b', line) or re.search(r'^[0-9]{3}[ ][0-9]{3}[ ][0-9]{4}$', line) or re.search(r'[(]\d{3}[)][ ]\d{3}-\d{4}', line)
        if (Match_Phone != None and query_info_LC == []):  


            for word in line.split():
                if (re.match(r'\b\d{3}-\d{3}-\d{4}\b', word)):
                   query_info_LC = Extractor.__query_INFO(word)[:]
            if (query_info_LC == []):
                match_obj =  re.search(r'[(]\d{3}[)][ ]\d{3}[-]\d{4}', line)
                if match_obj == None:
                    match_obj = re.search(r'^[0-9]{3}[ ][0-9]{3}[ ][0-9]{4}$', line)
                    
                
                phone_number = match_obj.group(0)
                query_info_LC = Extractor.__query_INFO(phone_number)[:]

        #Extract Date of Purchase
        match_Date = re.search(r'\b(1[0-2]|0[1-9])-(3[01]|[12][0-9]|0[1-9])-[0-9]{4}\b', line) or re.search(r'\b(1[0-2]|0[1-9]|[1-9])[/-](3[01]|[12][0-9]|0[1-9])[/-][0-9]{2}\b', line)
        if (match_Date != None and purchase_date_LC == None):

            for word in line.split():
                if (re.match(r'\b(1[0-2]|0[1-9])-(3[01]|[12][0-9]|0[1-9])-[0-9]{4}\b', word)):
                   purchase_date_LC = word
            for word in line.split():  
                if (re.match(r'\b(1[0-2]|0[1-9])[/-](3[01]|[12][0-9]|0[1-9])[/-][0-9]{2}\b', word)):
                   purchase_date_LC = word
            for word in line.split():
                if (re.match(r'\b([1-9])[/-](3[01]|[12][0-9]|0[1-9])[/-][0-9]{2}\b', word)):
                   purchase_date_LC = word
                   purchase_date_LC = '0' + purchase_date_LC

            if Extractor.__is_number(purchase_date_LC[0]) != True:
                purchase_date_LC = purchase_date_LC[-1:]
            elif Extractor.__is_number(purchase_date_LC[len(purchase_date_LC) - 1]) != True:
                purchase_date_LC = purchase_date_LC[:-1]    

        Line_Number += 1

     if total_cost_LC == None or tax_amount_LC == None or len(query_info_LC) == 0:
         return False
     else:
         if (purchase_date_LC == None):
              purchase_date_LC = '00/00/0000'
         elif (len(purchase_date_LC) == 8):
              purchase_date_LC = purchase_date_LC[:6] + '20' + purchase_date_LC[6:]           
         
         business_name_LC = query_info_LC[0]
         category_LC = query_info_LC[1]

         Extractor.__data_DICT[img_test_ID[:-4]] = [
             purchase_date_LC, 
             business_name_LC,
             category_LC,
             tax_amount_LC,
             total_cost_LC,
            ]
         return True



  def __query_INFO(search_parameter):
    
     gmaps = client(key = Extractor.__API_KEY)
     #Query google API by parameter_type
     query_DATA = []

     query_results = client.find_place(gmaps, ('+1' + search_parameter) , 'phonenumber', ['name', 'types'])        
     for item in query_results.items():
        query_DATA.append(item[1][0]['name'])
        query_DATA.append(item[1][0]['types'][0]) 
        return query_DATA

  def __OCR_ROUTINE_DEFAULT(img_ID, scale_percent):    

     TEST_IMG_PATH =  './test_images/' + img_ID[:-4] + "_TM.jpg"
         
     # Modify DPI
     receiptIMG = Image.open( './test_images/' + img_ID)
     receiptIMG.save(TEST_IMG_PATH, dpi = (300,300))
     img_modified = cv2.imread(TEST_IMG_PATH)
     os.remove(TEST_IMG_PATH)

     # Modify Size
     width = int(img_modified.shape[1] * scale_percent / 100)
     height = int(img_modified.shape[0] * scale_percent / 100)
     dim = (width, height)
     resized = cv2.resize(img_modified, dim, interpolation = cv2.INTER_AREA) 

     # Convert to Grayscale
     gray = cv2.cvtColor(resized, cv2.COLOR_BGR2GRAY)
     
     # Binarize
     thresholded = thresholding(gray)

     # deskew
     deskewed = deskew(thresholded)
       
     # execute tesseract-OCR
     data = pytesseract.image_to_string(deskewed, config=Extractor.__custom_config)
     data_file = open("./extraction_data/" + img_ID + "_RTD.txt", "w")
     n = data_file.write(data)
     data_file.close()

  def __OCR_ROUTINE_GCP_VISION(img_ID):

    #instantiates a client
    client = vision.ImageAnnotatorClient()

    #Create txt file object
    text_file = open("./extraction_data/cloud-vision-output.txt", "w")

    #The name of the image file to annotate
    FILE_NAME = os.path.abspath('./test_images/' + img_ID[:-4] + '.jpg')

    #Loads the image into memory
    with io.open(FILE_NAME, 'rb') as image_file:
        content = image_file.read()

    image = vision.Image(content=content)

    #performs label detection on the image file
    response = client.text_detection(image=image)
    texts = response.text_annotations

    #write to text file
    for text in texts:
        text_file.write('{}'.format(text.description))
        break


     




















   


   




  




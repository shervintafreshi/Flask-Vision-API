
import os 
import json
import pandas as pd
import urllib.request
import firebase_admin
import concurrent.futures
from uuid import uuid4
from firebase_admin import credentials
from firebase_admin import db
from firebase_admin import storage
from google.cloud import storage as google_storage

os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = r'btr490-project-firebase-adminsdk-3xbj4-61e9e79cb7.json'
cred = credentials.Certificate('btr490-project-firebase-adminsdk-3xbj4-61e9e79cb7.json')
firebase_admin.initialize_app(cred, {'databaseURL': 'https://btr490-project.firebaseio.com/', 'storageBucket': 'btr490-project.appspot.com'})

storage_client = google_storage.Client()
bucket = storage_client.get_bucket(storage.bucket())


def retrieve_USERS_PROTOCOL(): 
    database_user_ref = db.reference('/Users')
    return database_user_ref.get()

def create_DOCUMENT_LIST_PROTOCOL(user_id):

    global bucket
    database_user_ref = db.reference('/Users')  
    users_diction = database_user_ref.get()
    json_path_list = []


    user_data = users_diction[user_id]
    selected_keys_list = user_data["SelectedFileKeys"]["keysArray"]

    files_list = user_data["Files"]

    for key in selected_keys_list:
        if files_list[key]["fileUrl"] == "URL not associated":

            data = []
            with open('./json_documents/{}.json'.format(files_list[key]["fileName"]), 'w') as outfile:
                
                json.dump(data, outfile)
                blob = bucket.blob('documents/{}.json'.format(files_list[key]["fileName"]))
                
                unique_id = uuid4()
                metadata = {"firebaseStorageDownloadTokens": unique_id}
                blob.metadata = metadata

                blob.upload_from_filename('./json_documents/{}.json'.format(files_list[key]["fileName"]))   
                fileName = '{}/fileUrl'.format(key)

                file_URI = 'gs://btr490-project.appspot.com/{}.json'.format(files_list[key]["fileName"])
                file_Reference = database_user_ref.child(user_id).child("Files").update({
                    fileName: file_URI
                })

        else:
            json_path_list.append(files_list[key]["fileName"] + ".json")

    return json_path_list    




def start_FETCHING_PROTOCOL(json_PATH_LIST = None, image_PATH_LIST = None):
    
    json_PATH_LIST = ['documents/' + path for path in json_PATH_LIST]
    image_PATH_LIST = ['Images/' + path for path in image_PATH_LIST]  

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.map(retrieve_document, json_PATH_LIST)
        executor.map(retrieve_image, image_PATH_LIST)


# Retrieve a documents
def retrieve_document(source_name):

    global bucket
    resource = bucket.blob(source_name)
    try:
       assert resource.exists()
    except:
       return
    resource.download_to_filename('./json_documents/' + source_name[-14:])


# Retrieve a single Image
def retrieve_image(source_name):
     
     global bucket
     resource = bucket.blob(source_name)
     try:
        assert resource.exists()
     except:
        return
     resource.download_to_filename('./test_images/' + source_name[-17:])

def start_aggregation_PROTOCOL(extraction_data_DICT, request_data_DICT):

    path = os.getcwd()

    for filename in os.listdir(path + '/json_documents'):
        if filename != '.keep':
            for extracted_item in extraction_data_DICT:
                for data_item in request_data_DICT.values():

                    data_ID = data_item['image_ID']
                    if data_ID[:-4] == extracted_item and extraction_data_DICT[extracted_item] is not None:
                        new_file = json_excel_conv(filename)
                        df = pd.read_excel('./excel_documents/' + filename[:-4] + '_UM.xlsx')                   
                        row_data = [{'Purchase Date':  extraction_data_DICT[data_ID[:-4]][0], 
                                    'Business Name':    extraction_data_DICT[data_ID[:-4]][1], 
                                    'Purchase Category':   extraction_data_DICT[data_ID[:-4]][2], 
                                    'Sub-Total': extraction_data_DICT[data_ID[:-4]][4] - extraction_data_DICT[data_ID[:-4]][3], 
                                    'Tax': extraction_data_DICT[data_ID[:-4]][3], 
                                    'Total': extraction_data_DICT[data_ID[:-4]][4]
                        }]

                        if new_file == True:
                            df = pd.DataFrame()
                        df = df.append(row_data, ignore_index=True)
                        df.to_excel(r'./modified_excel_documents/' + filename[:-5] + '_M.xlsx',index=None, header=True) 
                 

def json_excel_conv(source_name):

    new_file = False

    try:
        df_2 = pd.read_json('./json_documents/' + source_name)
    except:
            new_file = True
            data = [{'Purchase Date':  "", 
                        'Business Name':    "", 
                        'Purchase Category':   "", 
                        'Sub-Total': "", 
                        'Tax': "", 
                        'Total': ""
            }]
            json_data = json.dumps(data)
            with open('./json_documents/{}'.format(source_name), mode='w') as f:
                f.write(json_data)
    df_2 = pd.read_json('./json_documents/' + source_name)
    df_2.to_excel(r'./excel_documents/' + source_name[:-4] + '_UM.xlsx', index=None, header=True)
    return new_file


def start_migration_PROTOCOL():
    global bucket
    for filename in os.listdir('./modified_excel_documents'):
        if filename != '.keep':
            df = pd.read_excel('./modified_excel_documents/' + filename)
            df.to_json('./modified_json_documents/' + filename[:-7] + '_TR.json', orient='columns', indent=4)
            document_blob = bucket.blob('documents/' + filename[:-7] + '.json')
            document_blob.upload_from_filename('./modified_json_documents/' + filename[:-7] + '_TR.json')


def task_report_PROTOCOL(request_data_DICT):
      
    path = os.getcwd()
    task_REPORT_DICT = ''
    id_MATCH = None
    file_number_original = 0
    file_number_modified = 0

    for filename in os.listdir('./modified_json_documents'):
        if filename != '.keep':
            file_number_original += 1

    for filename in os.listdir('./json_documents'):
        if filename != '.keep':
            file_number_modified += 1

    if file_number_modified == file_number_original:
        task_REPORT_DICT = 'Successfully Scanned'
        
    else:
        task_REPORT_DICT = 'Failed To Scan'
    
    reset_PROTOCOL()
    return task_REPORT_DICT
      

def reset_PROTOCOL():

     path = os.getcwd()
     for filename in os.listdir(path + '/excel_documents'):
         if filename != '.keep':
            os.remove(path + '/excel_documents/' + filename)   
     for filename in os.listdir(path + '/extraction_data'):
         if filename != '.keep':
            os.remove(path + '/extraction_data/' + filename)   
     for filename in os.listdir(path + '/json_documents'):
         if filename != '.keep':
            os.remove(path + '/json_documents/' + filename)    
     for filename in os.listdir(path + '/test_images'):
         if filename != '.keep':
            os.remove(path + '/test_images/' + filename)
     for filename in os.listdir(path + '/modified_excel_documents'):
         if filename != '.keep':    
            os.remove(path + '/modified_excel_documents/' + filename)
     for filename in os.listdir(path + '/modified_json_documents'):
         if filename != '.keep':
            os.remove(path + '/modified_json_documents/' + filename)     


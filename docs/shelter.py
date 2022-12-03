import pymongo
from pymongo import MongoClient
from bson.objectid import ObjectId

class AnimalShelter(object):
    """CRUD operations for Animal collection in MongoDB"""

    def __init__(self, username, password):
        # database login for user created in mongoDB client, will use script program to login.
            self.client = MongoClient('mongodb://%s:%s@localhost:27017/AAC' % (username, password))
            # Client connected to the databse
            self.database = self.client['AAC']
            print("connected to Database")
       
            
    # Create method to implement the C in CRUD.
    def create(self, data):
        # if data is not empty
        if data is not None:
            # insert method to create
            insert_dictionary = self.database.animals.insert_one(
                data
            )  # data should be dictionary
            if insert_dictionary != 0:
                return True
            else:
                return False
        else:
            raise Exception("Nothing to save, because data parameter is empty")

    # Method to implement the R in CRUD
    def read(self, target):  # default search criteria is empty
        try:
            if target is not None:
                # find method to read
                read_result = list(self.database.animals.find(target, {"_id": False}))
                return read_result
            else:
                raise Exception("Emapy")
                return False
        except Exception as e:
             print("Error: ", e)                                                              
    
    # Method to implement the U in CRUD (Update)
    # Use save function to update object according to _id property
    def update(self, field, save):
        if save is not None:
            if save:
                # insert method to update
                result = self.database.animals.insert_one(save)
            return result;
        else:
            raise Exception("Nothing to update, save is empty")
            
    
    # Method to implement the D in CRUD (Delete)
    def delete(self, remove):
        if remove is not None:
            if remove:
                # delete one method to only delte one.
                result = self.database.animals.delete_one(remove)
        else:
            raise Exception("Nothing to delete, remove is empty")
            
            #create method to find mongo datbase
    def find(self, target):
        try: 
            if target is not None:
                #metod to find
                find_result = list(self.database.animals.find(target, {"_id": False}))
                return find_result
            else:
                raise Exception("Emapy")
                return False
        except Exception as e:
             print("Error: ", e)
                

    def sort(self, target):
        try:
            if target is not None:
                sort_result = list(self.database.animals.find().sort(target, pymongo.ASCENDING))
                return sort_result
            else:
                raise Exception("Emapy")
                return False
        except Exception as e:
             print("Error: ", e)
            
                
                
               
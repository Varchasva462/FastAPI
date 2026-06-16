from email.policy import default

from fastapi import FastAPI,Path ,HTTPException,Query
import json, logging
from typing import Annotated,Literal,Optional
from fastapi.responses import JSONResponse 
from pydantic import BaseModel,Field,computed_field
from prometheus_fastapi_instrumentator import Instrumentator

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")  #logging.INFO sets minimum threshold for which messages will record
logger=logging.getLogger("fastapi-app")

app=FastAPI()       

Instrumentator().instrument(app).expose(app)

def load_data():
    with open("patients.json" , 'r') as f:
        data= json.load(f)
        
    return data

def save_data(data):
    with open("patients.json",'w') as f:
        json.dump(data,f)    

@app.get("/")
def hello():
    logger.info("Hello endpoint was hit")
    return{"messgae":"Patient management system API"}

@app.get("/about")
def about():
    logger.info("About endpoint was hit")
    return {"message":"API to manage patient records"}

@app.get("/view")
def view():
    logger.info("View endpoint was hit")
    data = load_data()
    active_patients=[]
    for patient in data.values():
        if patient.get(("is_active") ,True):
            active_patients.append(patient)
    
    return active_patients

@app.get("/patient/{patient_id}")
def view_patient(patient_id : str= Path(..., description = 'ID of the patient', example = 'P001')):
    logger.info("Patient ID was fetched")
    data=load_data()
    if patient_id not in data or data[patient_id].get("is_active" , True)== False :
         raise HTTPException(status_code=404, detail="patient not found")
    else :
        return data[patient_id]
    
    """ if patient_id in data:
        return data[patient_id]
    raise HTTPException(status_code=404, detail="patient not found")  """

@app.get("/sort")
def sort_patients(sort_by : str= Query(...,description='Sort on the basis of height,weight,bmi'),order: str=Query('asc',description='sort in asc or desc order')):
    logger.info("Sorted list was called")

    valid_fields=['height','weight','bmi']

    if sort_by not in valid_fields:
        raise HTTPException(status_code=400,detail=f'Invalid, select from {valid_fields}')
    
    if order not in ['asc','desc']:
        raise HTTPException(status_code=400,detail="Invalid order, select from asc or desc")
    
    data=load_data()

    sort_order=True if order=='desc' else False 
    active_patients = [ ]
    for patient in data.values():
      if patient.get("is_active" , True) :
        active_patients.append(patient)
    

    sorted_data= sorted(active_patients,key=lambda x:x.get(sort_by,0),reverse=sort_order)

    return sorted_data

#pydantic model
class Patient(BaseModel):
   
    id : Annotated[str, Field(...,description='ID of the patient',example='P001')]
    name : Annotated[str,Field(...,description='Name of the patient')]
    city : Annotated[str, Field(...,description='City where the patient lives')]
    age : Annotated[int , Field(...,gt=0,lt=120)]
    gender : Annotated[Literal['male','female'], Field(...)]
    height : Annotated[float, Field(...,gt=0,description='In meters')] 
    weight : Annotated[float, Field(...,gt=0,description='In kgs')]
    is_active : Annotated[bool,Field(default=True ,description="either True or False")]

    @computed_field
    @property
    def bmi(self)->float:
        bmi=round(self.weight/(self.height**2),2)
        return bmi

    @computed_field
    @property
    def verdict(self)->str:
        if self.bmi<18.5:
            return 'Underweight'
        elif self.bmi<25:
            return 'Normal'
        else:
            return 'Obese'
        
@app.post('/create')
def create_patient(patient:Patient):
    logger.info("New post was created")
    data=load_data()
    if patient.id in data:
        raise HTTPException(status_code=400,detail='Patient already exists')
    data[patient.id]=patient.model_dump(exclude=['id'])
    save_data(data)

    return JSONResponse(status_code=201, content='Patient successfully created')


class PatientUpdate(BaseModel):
         name : Annotated[Optional[str],Field(default=None)]
         city : Annotated[Optional[str], Field(default=None)]
         age : Annotated[Optional[int] , Field(default=None,gt=0)]
         gender : Annotated[Optional[Literal['male','female']], Field(default=None)]
         height : Annotated[Optional[float], Field(default=None,gt=0)] 
         weight : Annotated[Optional[float], Field(default=None,gt=0)]
         is_active : Annotated[Optional[bool], Field(default=None)]
    
@app.put("/edit/{patient_id}")
def update_patient(patient_id:str,patient_update:PatientUpdate):   #patient_update needs to be converted to dictionary
    logger.info("Patient info was edited")
    
    data=load_data()

    if patient_id not in data or data[patient_id].get("is_active",True) == False:
        raise HTTPException(status_code=404,detail='Patient not found')
    
    existing_patient_info = data[patient_id]

    updated_patient_info = patient_update.model_dump(exclude_unset=True) #exclude_unset so that only the fields sent by client gets loaded

    for key,value in updated_patient_info.items():
        existing_patient_info[key]=value  

    existing_patient_info['id']=patient_id
    patient_pydantic_obj=Patient(**existing_patient_info) #to calc. bmi,verdict
    existing_patient_info = patient_pydantic_obj.model_dump(exclude='id') # made dictionary again

    data[patient_id]=existing_patient_info 

    save_data(data)

    return JSONResponse(status_code=200,content={'message':'Patient info updated'})


@app.delete('/delete/{patient_id}')
def delete_patient(patient_id:str):
    logger.info("Patient data was deleted")
    
    data=load_data()

    if patient_id not in data:
        raise HTTPException(status_code=404,detail='Patient not found')
    
    data[patient_id]["is_active"] = False
    #del data[patient_id]

    save_data(data)

    return JSONResponse(status_code=200,content={'message':'Patient info Deleted'})









    


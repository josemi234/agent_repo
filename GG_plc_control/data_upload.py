##fxs para parsear y subir data a la base
#se correra en paralelo a la fx de control (lee y escribe)
## debe obtener 3 parametros desde el main thread: variables_info, variables_statuses y timestamp
from MySQL_adapter.MysqlConnectorAdapter import MysqlConnectorAdapter
from multiprocessing import Queue
import logging
import threading
import traceback
import time
import json

log = logging.getLogger()

class Data_uploader():

    def __init__(self, cm_ID, database_info, shared_storage, plc_id, variables, registers, devices): #en la cola se agregaran diccionarios
        self.ID = cm_ID  #id clickiemota
        self.database_info = database_info
        self.storage = shared_storage
        self.info_plcs = plc_id # mapea nombres_plcs:IDs
        self.variables_info = variables # el json de variables 
        self.registers = registers #info "device_types"
        self.to_upload = []

        #correspondencia entre master y dev type
        dev_types = {}
        for dev in devices:
            dev_info = devices[dev]
            dev_class = dev_info["device_type"]
            dev_types.update({dev:dev_class})

        self.dev_classes = dev_types

    def parse_data(self):
         upload_flag = False

         #getting oldest dta from queue
         if self.storage.qsize() >0:

            log.info("[DATA UPLOADER] There is data to upload, parsing...")

            upload_flag = True
            info = self.storage.get()
            current_values = info["current_values"]
            desired_statuses = info["configured_values"]
            controllers_info = info["control_results"]
            timestamp = info["timestamp"]
            #parseo info controladores
            if len(controllers_info) > 0:
                log.info(f"[DATA UPLOADER] parsing controlllers data")
                for controller in controllers_info: 
                    control_info = controllers_info[controller]
                    auto = control_info["automode"]
                    if auto is not None:
                        automode = (auto, timestamp, controller+"_automode", self.ID)
                        self.to_upload.append(automode)
                    law = control_info["applied_law"]
                    if law is not None:
                        result = (law, timestamp, controller+"_applied_law", self.ID)
                        self.to_upload.append(result)
            
            #parseo las variables leidas: #PROBAR
            if len(current_values) > 0:
                log.info(f"[DATA UPLOADER] parsing data from variables readed values")
                for variable in current_values:
                    #aqui re defino el label (variable)
                    var_info = self.variables_info[variable]
                    var_dev = self.dev_classes[var_info["master"]]
                    bit_id = var_info.get("bit", None)

                    var_id = var_info.get("label", None)
                    if var_id is not None:
                        label = var_id
                    else: 
                        label = self.registers[var_dev]["registers"][var_info["register"]]["label"]

                    # if bit_id is not None:
                    #     label = str(self.registers[var_dev]["registers"][var_info["register"]]["label"]) + str(bit_id)
                    # else:
                    #     label = self.registers[var_dev]["registers"][var_info["register"]]["label"]

                    dev_id = self.info_plcs[self.variables_info[variable]["master"]]
                    value = current_values[variable]
                    if value is not None:
                        dta = (value, timestamp, label, dev_id)
                        self.to_upload.append(dta)

            #parseo los desired status: #PROBAR
            for str_de_variables in desired_statuses:
                 log.info(f"[DATA UPLOADER] Parsing data from variables desired status")
                 variables = str_de_variables.replace(" ", "").split(",")
                 for var in variables:
                    name, value = var.split("=")
                    var_info = self.variables_info[name]
                    if value is not None:
                        dev_id = self.info_plcs[self.variables_info[name]["master"]]
                        var_dev = self.dev_classes[var_info["master"]]

                        bit_id = var_info.get("bit", None)
                        var_id = var_info.get("label", None)

                        if var_id is not None:
                            label = var_id+"_desired_status"

                        else:
                            label = str(self.registers[var_dev]["registers"][var_info["register"]]["label"])+"_desired_status"
                        
                        # if bit_id is not None:
                        #     label = str(self.registers[var_dev]["registers"][var_info["register"]]["label"])+str(bit_id)+"_desired_status"
                        # else:
                        #     label = str(self.registers[var_dev]["registers"][var_info["register"]]["label"])+"_desired_status"

                        dta = (int(value), timestamp, label, dev_id) ##name+"_desired_status"
                        self.to_upload.append(dta)

         return upload_flag

    def check_rows(self, db_interface):
        log.info("[DATA UPLOADER] Checking if there is space in recents table ...")
        db_table = self.database_info["recents_table"]["name"]
        row_count = db_interface.get_row_count(db_table)
        max_rows = self.database_info["recents_table"]["max_rows"]
        if row_count > max_rows:
            log.info(" [DATA UPLOADER] --> Recents table is full, making some space")
            db_interface.delete_data(
                    db_table, add_query=' ORDER BY t DESC LIMIT {}'.format(row_count - max_rows))
            log.info("[DATA UPLOADER] --> Older rows have been deleted.")

        else:
            log.info("Recents table has enough space!")

    def upload_nodb(self, flag):
        if flag:
            log.info("[DATA UPLOADER] >>>>>>>>>> DATA PROCESSED:")
            print(self.to_upload)

        else: 
            log.info("[DATA UPLOADER] >>>>>>>> NO HAY DTA POR SUBIR C:")
            print(self.to_upload)

    def upload(self, flag):

        if flag:
            log.info("[DATA UPLOADER] trying to upload values to recents table...")
            #connectar a la base
            db_name = self.database_info["database_name"]
            db_table = self.database_info["recents_table"]["name"]
            db_user = "Clickie"
            db_password = "ClickieBBDDmanager"
            db_host = "localhost"
            db_interface = MysqlConnectorAdapter(db_name, db_user, db_password, db_host)
            
            try:
                db_interface.upload_data(db_table, self.to_upload)
                log.info("[DATA UPLOADER] --> Data has been uploaded!")
                self.to_upload  = []

            except Exception: 
                Err = traceback.format_exc()
                log.info(f"[ERROR] [DATA UPLOADER] An error occurred while uploading values: {Err}")

            #check recents number of rows:
            try:
                self.check_rows(db_interface)
                db_interface.closing()
                log.info("[DATA UPLOADER] DB connection closed")

            except Exception:
                Err = traceback.format_exc()
                log.info(f"[ERROR] [DATA UPLOADER] An error ocurred while checking rows: {Err}")

        else:
            log.info("[DATA UPLOADER] No data to upload, skipping processs")


def periodic_data_upload(storage, pth):

    log.info("[DATA UPLOADER] Starting periodic data upload thread ...")

    with open(pth,"r") as c_file:
                info_json = json.load(c_file)
    db_info =  info_json["database"]

    while True: 

        try:
            log.info("[DATA UPLOADER] Trying to upload data to database")
            with open(pth,"r") as c_file:
                    conf_json = json.load(c_file)
    
            registers_info = conf_json["lambda_functions"]["GG_plc_controller"]["device_types"]
            devices = conf_json["lambda_functions"]["GG_plc_controller"]["devices"]
            variables = conf_json["lambda_functions"]["GG_plc_controller"]["variables"]
            clickiemota_id = conf_json["id"]
            # map the device names to ids:
            dev_ids = {}
            for dev in devices:
                dev_ids.update({dev:devices[dev]["id"]})
    
            #start the uploading process:
            uploader = Data_uploader(clickiemota_id, db_info, storage, dev_ids, variables, registers_info, devices)
            flag = uploader.parse_data()
            uploader.upload(flag)
    
            log.info("[DATA UPLOADER] uploading data again in 60s")
            time.sleep(60)

        except:
            err = traceback.format_exc()
            log.info(f"[DATA UPLOADER] An error occurred while uploading data: \n {err}")
            time.sleep(20)

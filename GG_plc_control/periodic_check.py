import json
import time
import logging
import traceback
import threading
from multiprocessing import Queue
from datetime import datetime
from protocols_utils import modbus_wrapper_RTU, modbus_wrapper_TCP
from MySQL_adapter.MysqlConnectorAdapter import MysqlConnectorAdapter
from serial_adapter.ModbusSerialClientAdapter import  ModbusSerialClientAdapter

#hint? usar metodos copy, pop y clear en listas
log = logging.getLogger()

#clase par leer periodicamente
class Periodic_checkout():

    def __init__(self, vars_to_read, registers, devices, hardware_settings):

        self.storage= [] #aqui se guardan los datos a subir
        self.variables  = vars_to_read #lo que se busca leer
        self.current_slave = None #se guarda el NOMBRE del ultimo slave conectado
        self.slave = None #objeto modbus del ultimo slave
        self.to_read = Queue() #se "encolan las tareas a leer"
        #info 
        self.registers_info = registers
        self.devices_info = devices
        self.hard_settings = hardware_settings #strict, handle_local_echo resource etc

    def sort_reading(self):
        #este metodo ordena las variables por slave dev
        log.info(f"[CHECK CONTEXT] sorting variables by slave unit")
        by_slave = {}
        for variable in self.variables:
            for thang in variable:
                info = variable[thang]
                slave = info["master"]

            if slave in by_slave.keys():
                by_slave[slave].update(variable)

            else:
                by_slave.update({slave: {}})
                by_slave[slave].update(variable)
        
        for clase in by_slave:
            variables_in_clase = by_slave[clase]
            for v in variables_in_clase:
                dta = {}
                dta.update({v: variables_in_clase[v]})
                self.to_read.put(dta) #se sube la tarea en la cola
        log.info("[CHECK CONTEXT] All the task has been uploaded to the queue")

    ###se debe modificar paraaceptar definir cualquier protocolo
    def define_rtu_slave(self):
        #crea el slave en rtu para poder conectarse c: 
        log.info("[CHECK CONTEXT] Defining the slave")
        slave_info = self.devices_info[self.current_slave]
        #ver protocolo
        protocol = slave_info["protocol"]
        #clausula if
        if protocol == "RTU":
            current_slave = modbus_wrapper_RTU(slave_info, self.hard_settings["resource"], self.hard_settings["handle_local_echo"])

        elif protocol == "TCP":
            current_slave = modbus_wrapper_TCP(slave_info)

        else: 
            pass 

        self.slave = current_slave 

    def read_variable(self):
       
        timestamp = int(datetime.timestamp(datetime.now()))
        #quito elemneto de la queue
        task  = self.to_read.get().popitem()
        log.info(f"[CHECK CONTEXT] Reading context variable: {task}")
        variable, info = task[0], task[1]
        slave = info["master"]
        var_id = info.get("label", None)
        #actualizo master si es necesario
        if slave != self.current_slave or self.current_slave == None:
            log.info(f"[CHECK CONTEXT] Must define a new slave for this operation: {slave}")
            self.current_slave = slave
            self.define_rtu_slave()

        slave_type = self.devices_info[slave]["device_type"]
        register = self.registers_info[slave_type]["registers"][info["register"]]
        bit = info.get("bit", None)
        value = self.slave.read_variable(register, bit)
        # luego se debe leer usando metodo read_variable de modbus_wrapper
        # finalmente se parsea el dato y se sube a la cola de sql
        dev_id = self.slave.id
        if value is not None:  
            if var_id is not None:
                label = var_id
            else:
                label = str(register["label"])
            # if bit is not None:
            #     label = str(register["label"]) + str(bit)
            # else:
            #     label = str(register["label"])

            dta = (value, timestamp, label, dev_id) #variable
            log.info(f"[CHECK CONTEXT] data leida: {dta}")
            self.storage.append(dta)

    def upload_data(self, db_info):
        #se copia la dta de storage y este se vacia
        log.info("[CHECK CONTEXT] Trying to upload data to recents table")
        upload = self.storage.copy()
        self.storage.clear()
        
        db_name = db_info["database_name"]
        db_table = db_info["recents_table"]["name"]
        db_user = "Clickie"
        db_password = "ClickieBBDDmanager"
        db_host = "localhost"
        db_interface = MysqlConnectorAdapter(db_name, db_user, db_password, db_host)
        
        try: 
            db_interface.upload_data(db_table, upload)
            log.info(f"[CHECK CONTEXT] data has been uploaded successfully!")
            db_interface.closing()
            log.info(f"[CHECK CONTEXT] Db connectio  closed.")
        except:
            err = traceback.format_exc()
            log.info(f"[CHECK CONTEXT] An error ocurred when trying to upload data: \n {err}")

    def upload_data_nodb(self,db_info):
        upload = self.storage.copy()
        self.storage.clear()
        print(f"COLLECTED DATA: \n {upload}")

#se crea el main() de este thread c:

def run(pth, event):

    log.info("[CHECK CONTEXT] the variable check is about to start")
    with open(pth, 'r') as f:
        lambda_info = json.load(f)

    to_read = []
    db_info = lambda_info["database"]
    lambda_confs = lambda_info["lambda_functions"]["GG_plc_controller"]
    registers = lambda_confs["device_types"]
    devices = lambda_confs["devices"]

    log.info(f"[CHECK CONTEXT] Collecting info from json file ...")
    controls = lambda_confs["control_laws"]
    for c in controls:
        c_info = controls[c]["check_variables"]
        for thang in c_info:
            thang_info = c_info[thang]
            up = {thang: thang_info}
            to_read.append(up)

    cm_settings = {"resource": lambda_confs.get("resource", "/dev/ttyS0"), "handle_local_echo": lambda_confs.get("handle_local_echo", False)}

    log.info(f"[CHECK CONTEXT] context variables are: {to_read}")
    checker = Periodic_checkout(to_read, registers,devices, cm_settings)
    checker.sort_reading()

    print(f"tamaño cola:{checker.to_read.qsize()} ")
    while checker.to_read.qsize()>0:

        if not event.is_set():
            log.info(f"[CHECK CONTEXT] Processing a task ...")
            try:
                checker.read_variable()
                t = len(checker.storage)
                log.info(f"[CHECK CONTEXT] AVALIABLE ROWS: {t}, \n rows: {checker.storage} ")
            except Exception:
                err = traceback.format_exc()
                log.info(f"[CHECK CONTEXT] An error occurred while executing task: \n {err}")
        
    if len(checker.storage)>0:
        log.info(f"[CHECK CONTEXT] There is data avaliable to upload: \n {checker.storage}")
        checker.upload_data(db_info)

def periodic_check(pth, event):
    log.info("[CHECK CONTEXT] Starting Thread to check context variables periodically")
    while True:
        
        time.sleep(60)
        try:
            run(pth, event)
            
        except Exception:
            err = traceback.format_exc()
            log.info(f"[ERROR][CHECK CONTEXT] An error ocurred during PERIODIC CHECK execution: \n {err}")




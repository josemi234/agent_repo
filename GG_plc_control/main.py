import time
from MySQL_adapter.MysqlConnectorAdapter import MysqlConnectorAdapter
from serial_adapter.ModbusSerialClientAdapter import  ModbusSerialClientAdapter
import json  
import logging
import traceback
from multiprocessing import Queue
from datetime import datetime
import schedule
import threading
from data_upload import periodic_data_upload
from periodic_check import periodic_check
from schedule_adapter.schedule_worker import (write_schedule, edit_schedule, start_schedule)
##import customs
import protocols_utils as protocols 

FORMAT = ('%(asctime)-15s %(threadName)-15s '
          '%(levelname)-8s %(module)-30s:%(lineno)-8s %(message)s')
logging.basicConfig(filename="logsexe.log",filemode="a", format=FORMAT)
log = logging.getLogger()
log.setLevel(logging.DEBUG)


pth = '/home/ggc_user/gg_configs/lambda_configs/lambda_config.json'
shared_storage = Queue()
lambda_name = "GG_plc_controller"
eve = threading.Event()

#fx corre en main thread (con scheduler)
def main(storage, pth, event):

    if not event.isSet():
        event.set()
        log.info(f"[PLC CONTROL] Setting event, value is: {event.isSet()}")

    result_to_upload = {} #current_values and configured values
    timestamp = int(datetime.timestamp(datetime.now()))
    result_to_upload.update({"timestamp": timestamp})

    time.sleep(0.1) #wait a littleto clean channel (just precaution measure)

    log.info("[PLC CONTROL] Starting main process function ... \n -> loading function information from json file")

    with open(pth, "r") as file:
        lambda_configs = json.load(file)


    lambda_configs = lambda_configs["lambda_functions"]["GG_plc_controller"]
    variables = lambda_configs["variables"]
    devices = lambda_configs["devices"]
    registers = lambda_configs["device_types"]
    controls = lambda_configs["control_laws"]
    dev_info = {"resource": lambda_configs.get("resource","/dev/ttyAMA2"), 
                "handle_local_echo": lambda_configs.get("handle_local_echo", False)}

    log.info("[PLC CONTROL] Information loaded sucessfully \n Starting to read variables ...")

    #initialize the plc controller:
    plc_controller = protocols.control_plcs(variables, devices, registers, controls, dev_info)

   #event.clear()
    log.info(f"[PLC CONTROL] Taking control of RTU channel. event state: {event.isSet()}")
    #Read the real value of variables:
    plc_controller.read_variables()
    log.info(f"[PLC CONTROL] Variables has been readed sucessfully: \n {plc_controller.variables_values} \n")


    #check the control conditions and change if neeeded:
    log.info("[PLC CONTROL] Checking control laws, changing variables values if needed ...")
    plc_controller.check_law()

    event.clear()
    log.info(f"[PLC CONTROL] channel has been released. event state: {event.isSet()}")

    result_to_upload.update({"current_values": plc_controller.variables_values})
    result_to_upload.update({"configured_values": plc_controller.variables_desired_statuses})
    result_to_upload.update({"control_results": plc_controller.control_statuses})

    storage.put(result_to_upload)

    print(f"[PLC CONTROL] RESULTS: \n {result_to_upload} \n")
    print("---"*17)

    #modificacion del schedule
    log.info("[PLC CONTROL] Verifying modification on schedule...")
    schedule_json = lambda_configs['schedule']
    log.info(f"[PLC CONTROL] schedule is: {schedule_json}")
    edit_schedule(schedule_json, schedule, lambda: main(storage, pth, event))

##############################

def Agendar(path_json, lambda_name, storage, event):
    print(f"[PLC CONTROL] iniciando agenda para {lambda_name}!")
    with open(path_json,"r") as c_file:
        conf_json = json.load(c_file)
    try:
        schedule_json = conf_json['lambda_functions'][lambda_name]['schedule']
        write_schedule(schedule_json, schedule, lambda: main(storage, path_json, event))
        start_schedule(schedule)
    except:
        err = traceback.format_exc()
        log.info(f"[PLC CONTROL] Unable to find schedule for {lambda_name} or and error was enconuntered \n retrying in 60ss ...")
        log.info(f"[PLC CONTROL] ERROR: \n {err}")
        time.sleep(60)
        Agendar(path_json, lambda_name, storage, event)

###iniciar thread de subida data:  db_info, storage, devices, variables

uploader = threading.Thread(target=periodic_data_upload, args=(shared_storage, pth))
uploader.start()

#se debe agregar el thread de las lecturas checking
check_contex = threading.Thread(target=periodic_check, args=(pth, eve))
check_contex.start()

#inicio chequeos periodicos de plc
Agendar(pth, lambda_name, shared_storage, eve)

#dummy handler
def lambda_method(event, context):
    return

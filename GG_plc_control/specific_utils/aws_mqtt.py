import json
import logging
import greengrasssdk
import sys

# Setup logging to stdout
logger = logging.getLogger(__name__)
logging.basicConfig(stream=sys.stdout, level=logging.DEBUG)

# Creating a greengrass core sdk client
client = greengrasssdk.client("iot-data")


def publish_to_mqtt(
        topic, payload_dict, queueFullPolicy="AllOrException",
        max_response_length=None):
    payload = json.dumps(payload_dict)
    payload_length = len(payload)
    if max_response_length and payload_length > max_response_length:
        while payload:
            (send, payload) = (
                payload[:max_response_length], payload[max_response_length:])
            try:
                client.publish(
                    topic=topic,
                    queueFullPolicy="AllOrException",
                    payload=payload,
                )
            except Exception as e:
                logger.error("Failed to publish message: " + repr(e))
                break
        return
    try:
        client.publish(
            topic=topic,
            queueFullPolicy="AllOrException",
            payload=payload,
        )
    except Exception as e:
        logger.error("Failed to publish message: " + repr(e))

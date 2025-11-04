from flask import Flask
from ots_debugger_plugin.rabbitmq_client import RabbitMQClient
from opentakserver.extensions import logger, socketio


class CoTListener(RabbitMQClient):
    def __init__(self, app: Flask):
        super().__init__(app)

    def on_channel_open(self, channel):
        logger.debug("rabbitmq channel open")
        self.rabbit_channel = channel
        # decare and bind to cot exchange/fanout topic
        self.rabbit_channel.queue_bind(
            exchange="cot_controller", queue="cot_controller"
        )
        ctag = self.rabbit_channel.basic_consume(
            queue="cot_controller",
            on_message_callback=self.on_message,
            auto_ack=True,
            consumer_tag="debugger_plugin",
        )
        logger.debug(f"debugger cot listener setup on consumer tag {ctag}")

    def on_message(self, unused_channel, basic_deliver, properties, body: bytes):
        socketio.emit("cot", body.decode(), namespace="/debugger")

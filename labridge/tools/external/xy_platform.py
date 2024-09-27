import json

from llama_index.core.llms import LLM
from llama_index.core import Settings
from llama_index.core.embeddings import BaseEmbedding

from labridge.tools.base.function_base_tools import CallBackBaseTool, FuncOutputWithLog
from labridge.tools.base.tool_log import ToolLog, TOOL_OP_DESCRIPTION, TOOL_REFERENCES
from labridge.callback.base.operation_log import (
    OperationOutputLog,
    OP_DESCRIPTION,
    OP_REFERENCES,
)
from labridge.interact.authorize.authorize import (
    operation_authorize,
    aoperation_authorize,
)
from labridge.callback.external.xy_platform import XYPlatformOperation

from typing import Any

import math
import serial


class PacketLayer:

    PACKET_TIMEOUT_MS = 60000
    PACKET_MAX_LENGTH = 255
    PACKET_MAGIC_NUMBER = 50
    PACKET_TYPE_OK = 0
    PACKET_TYPE_APP = 1
    PACKET_TYPE_ECHO = 16

    def __init__(self) -> None:

        from serial.tools import list_ports

        for pinfo in list_ports.comports():
            if pinfo.description.startswith("USB-Enhanced-SERIAL-B CH342"):
                print("CH342 Virtual COM Port B Detected")
                selected_port = pinfo.name

        self.serial_app = serial.Serial(
            selected_port,
            baudrate=115200,
            bytesize=serial.EIGHTBITS,
            parity=serial.PARITY_NONE,
            stopbits=serial.STOPBITS_ONE,
            timeout=self.PACKET_TIMEOUT_MS / 1000,
        )

    def send(self, serial_number, packet_type, content):
        content_len = len(content)
        assert content_len <= self.PACKET_MAX_LENGTH
        tx = bytes(
            [
                self.PACKET_MAGIC_NUMBER,
                serial_number,
                packet_type,
                content_len,
                *content,
            ]
        )
        self.serial_app.write(tx)

    def recv(self):
        rx_header = self.serial_app.read(4)
        assert len(rx_header) == 4, rx_header
        magic_number, serial_number, packet_type, content_len = rx_header
        assert magic_number == self.PACKET_MAGIC_NUMBER, magic_number
        content = self.serial_app.read(content_len)
        assert len(content) == content_len, (content_len, content)
        return serial_number, packet_type, content


class AppLayer:

    CONTENT_TYPE_UART = 0x00
    CONTENT_TYPE_TEST = 0x01
    CONTENT_TYPE_PULSE = 0x02

    def __init__(self) -> None:
        self.packet_layer = PacketLayer()

    def send(self, app_content_type, app_content):
        self.packet_layer.send(
            0, self.packet_layer.PACKET_TYPE_APP, [app_content_type, *app_content]
        )


class MotorUART:
    def __init__(self) -> None:
        self.app_layer = AppLayer()

    def send(self, cmd):
        self.app_layer.send(self.app_layer.CONTENT_TYPE_UART, cmd)
        _, _, response = self.app_layer.packet_layer.recv()
        return response

    def enable(
        self,
    ):
        res = self.send([0x01, 0xF3, 0xAB, 0x01, 0x00, 0x6B])
        assert res == bytes([0x01, 0xF3, 0x02, 0x6B]), res.hex()

    def disable(
        self,
    ):
        res = self.send([0x01, 0xF3, 0xAB, 0x00, 0x00, 0x6B])
        assert res == bytes([0x01, 0xF3, 0x02, 0x6B]), res.hex()

    def speed(self, speed: int, acc: int = 0x0A):
        res = self.send(
            [0x01, 0xF6, 0x01, speed // 0x100, speed % 0x100, acc, 0x00, 0x6B]
        )
        assert res == bytes([0x01, 0xF6, 0x02, 0x6B]), res.hex()

    def position(
        self, position, dir=0, speed: int = 0x100, acc: int = 0x0A, pos_mode=1
    ):
        res = self.send(
            [
                0x01,
                0xFD,
                dir,
                speed // 0x100,
                speed % 0x100,
                acc,
                position // 0x1000000,
                (position % 0x1000000) // 0x10000,
                (position % 0x10000) // 0x100,
                (position % 0x100),
                pos_mode,
                0x00,
                0x6B,
            ]
        )
        assert res == bytes([0x01, 0xFD, 0x02, 0x6B]), res.hex()

    def driver_params_read(
        self,
    ):
        res = self.send([0x01, 0x42, 0x6C, 0x6B])
        return res

    def zero_params_read(
        self,
    ):
        res = self.send([0x01, 0x22, 0x6B])
        return res

    def zero_params_write(self, dir=0, speed=30):
        cmd = b"\x01\x4C\xAE\x01"
        cmd += b"\x03"  # 回零模式为 Endstop 多圈触发回零
        cmd += bytes([dir])
        cmd += bytes([speed // 0x100, speed % 0x100])
        cmd += b"\x00\x00\x27\x10\x01\x2c\x03\x20\x00\x3c\x00\x6b"

        res = self.send(cmd)
        assert res == bytes([0x01, 0x4C, 0x02, 0x6B]), res.hex()

    def zero_status_read(
        self,
    ):
        res = self.send(bytes([0x01, 0x3B, 0x6B]))
        return res

    def zero_act(
        self,
    ):
        res = self.send([0x01, 0x9A, 0x03, 0x00, 0x6B])
        assert res == bytes([0x01, 0x9A, 0x02, 0x6B]), res.hex()

    def stop(
        self,
    ):
        res = self.send([0x01, 0xFE, 0x98, 0x00, 0x6B])
        assert res == bytes([0x01, 0xFE, 0x02, 0x6B]), res.hex()


class MotorPulse:
    def __init__(self) -> None:
        self.app_layer = AppLayer()

    def move(self, time_sec, pulses):
        cmd = bytes()
        time_us: int = math.floor(time_sec * 1000000)
        cmd += time_us.to_bytes(length=4, byteorder="little")
        for motor_index, motor_pulse in pulses:
            cmd += motor_index.to_bytes(length=1, byteorder="little")
            cmd += motor_pulse.to_bytes(length=4, byteorder="little", signed=True)
        self.app_layer.send(self.app_layer.CONTENT_TYPE_PULSE, cmd)
        self.app_layer.packet_layer.recv()


class XYPlatform:
    def __init__(self, motor_a=0, motor_b=1, speed=200) -> None:
        self.motor_pulse = MotorPulse()
        self.motor_a = motor_a
        self.motor_b = motor_b
        self.x, self.y = 0, 0
        self.speed = speed

    def move(self, dx, dy):
        self.x += dx
        self.y += dy
        ratio = 80
        speed = self.speed  # mm/s
        da = math.floor(ratio * (-dx + dy))
        db = math.floor(ratio * (-dx - dy))
        move_length = math.sqrt(dx**2 + dy**2)
        move_time = move_length / speed
        self.motor_pulse.move(move_time, [[self.motor_a, da], [self.motor_b, db]])

    def move_to(self, x, y):
        dx = x - self.x
        dy = y - self.y
        self.move(dx, dy)

    def set_zero(self):
        self.x, self.y = 0, 0


xy = XYPlatform(speed=50)


class XYPlatformMoveTool(CallBackBaseTool):
    r"""
    This tool is used to move a motorized XY stage, the motorized XY stage can be moved along the `X` axis and `Y` axis.

    Args:
            llm (LLM): The used LLM. If not specified, the `Settings.llm` will be used.
            embed_model (BaseEmbedding): The used embedding model. If not specified, the `Settings.embed_model` will be used.
            verbose (bool): Whether to show the inner progress.
    """

    def __init__(
        self,
        llm: LLM = None,
        embed_model: BaseEmbedding = None,
        verbose: bool = False,
    ):
        self._llm = llm or Settings.llm
        self._embed_model = embed_model or Settings.embed_model
        self._verbose = verbose
        super().__init__(
            fn=self.move,
            async_fn=self.amove,
            tool_name=XYPlatformMoveTool.__name__,
            callback_operation=XYPlatformOperation,
        )

    def log(self, **kwargs: Any) -> ToolLog:
        op_log = kwargs["operation_log"]
        if not isinstance(op_log, OperationOutputLog):
            raise ValueError("operation_log must be 'OperationLog'.")
        log_to_user = op_log.log_to_user
        log_to_system = op_log.log_to_system
        return ToolLog(
            tool_name=self.metadata.name,
            log_to_user=log_to_user,
            log_to_system=log_to_system,
        )

    def move(
        self,
        user_id: str,
        x_direction: int,
        x_movement: int,
        y_direction: int,
        y_movement: int,
    ) -> FuncOutputWithLog:
        r"""
        This tool is used to move a motorized XY stage along the `X` axis and `Y` axis.

        Args:
                user_id: The user id of a Lab member.
                x_direction (int): An integer representing the moving direction in `x` axis. 0 means moving to left, 1 means moving to right.
                x_movement (int): The distance moved along `x` axis. unit: millimeter.
                        If there is no need to move along `x` axis, use integer 0 as the input.
                y_direction (int): An integer representing the moving direction in `y` axis. 0 means moving down, 1 means moving up.
                y_movement (int): The distance moved along `y` axis. unit: millimeter.
                        If there is no need to move along `y` axis, use integer 0 as the input.

        Returns:
                FuncOutputWithLog: The output and log.
        """
        # This docstring is used as the tool description.
        op_name = self._callback_operation.__name__
        kwargs = {
            "x_direction": x_direction,
            "x_movement": x_movement,
            "y_direction": y_direction,
            "y_movement": y_movement,
        }

        kwargs_str = json.dumps(kwargs)
        operation_log = operation_authorize(
            user_id=user_id,
            op_name=op_name,
            kwargs_str=kwargs_str,
            llm=self._llm,
            embed_model=self._embed_model,
            verbose=self._verbose,
        )
        log_dict = {"operation_log": operation_log}

        dx = x_movement
        dx *= 1 if x_direction == 0 else -1
        dy = y_movement
        dy *= 1 if y_direction == 0 else -1
        try:
            xy.move(dx, dy)
        except Exception as e:
            print(f"{e}")

        return FuncOutputWithLog(
            fn_output=f"Have successfully moved the motorized XY stage according to the instruct of the user {user_id}",
            fn_log=log_dict,
        )

    async def amove(
        self,
        user_id: str,
        x_direction: int,
        x_movement: int,
        y_direction: int,
        y_movement: int,
    ) -> FuncOutputWithLog:
        r"""
        This tool is used to move a motorized XY stage along the `X` axis and `Y` axis.

        Args:
                user_id: The user id of a Lab member.
                x_direction (int): An integer representing the moving direction in `x` axis. 0 means moving to left, 1 means moving to right.
                x_movement (int): The distance moved along `x` axis. unit: millimeter.
                        If there is no need to move along `x` axis, use integer 0 as the input.
                y_direction (int): An integer representing the moving direction in `y` axis. 0 means moving down, 1 means moving up.
                y_movement (int): The distance moved along `y` axis. unit: millimeter.
                        If there is no need to move along `y` axis, use integer 0 as the input.

        Returns:
                FuncOutputWithLog: The output and log.
        """
        # This docstring is used as the tool description.
        op_name = self._callback_operation.__name__
        kwargs = {
            "x_direction": x_direction,
            "x_movement": x_movement,
            "y_direction": y_direction,
            "y_movement": y_movement,
        }

        kwargs_str = json.dumps(kwargs)
        operation_log = await aoperation_authorize(
            user_id=user_id,
            op_name=op_name,
            kwargs_str=kwargs_str,
            llm=self._llm,
            embed_model=self._embed_model,
            verbose=self._verbose,
        )
        log_dict = {"operation_log": operation_log}

        dx = x_movement
        dx *= 1 if x_direction == 0 else -1
        dy = y_movement
        dy *= 1 if y_direction == 0 else -1
        try:
            xy.move(dx, dy)
        except Exception as e:
            print(f"{e}")

        return FuncOutputWithLog(
            fn_output=f"Have successfully moved the motorized XY stage according to the instruct of the user {user_id}",
            fn_log=log_dict,
        )

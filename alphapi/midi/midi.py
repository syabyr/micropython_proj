import ubluetooth
import struct
from machine import Pin, PWM
import time
from micropython import const


led_pin = Pin(12,Pin.OUT) # blue led
led2_pin = Pin(13,Pin.OUT) # blue led

# BLE UUID 定义
MIDI_SERVICE_UUID = ubluetooth.UUID("03B80E5A-EDE8-4B33-A751-6CE34EC4C700")
MIDI_CHARACTERISTIC_UUID = ubluetooth.UUID("7772E5DB-3868-4112-A1A9-F2669D106BF3")

PPQN = const(0x60)
QUARTER_NOTE_MS = const(500)  # 默认 120 BPM

# 更悦耳的测试旋律（Ode to Joy，公有领域）：(note, duration_ticks)
MELODY = (
    (64, 96), (64, 96), (65, 96), (67, 96),
    (67, 96), (65, 96), (64, 96), (62, 96),
    (60, 96), (60, 96), (62, 96), (64, 96),
    (64, 144), (62, 48), (62, 192),

    (64, 96), (64, 96), (65, 96), (67, 96),
    (67, 96), (65, 96), (64, 96), (62, 96),
    (60, 96), (60, 96), (62, 96), (64, 96),
    (62, 144), (60, 48), (60, 192),
)


def build_track_events(melody, velocity=0x64):
    events = []
    for note, duration_ticks in melody:
        events.append((0x00, 0x90, note, velocity))
        events.append((duration_ticks, 0x80, note, velocity))
    return tuple(events)


TRACK_EVENTS = build_track_events(MELODY)

# 事件常量
_IRQ_CENTRAL_CONNECT = const(1)
_IRQ_CENTRAL_DISCONNECT = const(2)
_IRQ_GATTS_WRITE = const(3)

NOTE_NAMES = ("C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B")


def note_to_name(note):
    base = NOTE_NAMES[note % 12]
    octave = note // 12 - 1
    return "{}{}".format(base, octave)


def ticks_to_ms(ticks):
    return (ticks * QUARTER_NOTE_MS) // PPQN

class BLEMidi:
    def __init__(self):
        self.ble = ubluetooth.BLE()
        self.ble.active(True)
        self.ble.irq(self._irq_handler)

        self.connected = False
        self.conn_handle = None
        self.notifications_enabled = False
        self.midi_cccd = None
        self._register()

    def _irq_handler(self, event, data):
        """ 处理 BLE 连接 / 断开事件 """
        if event == _IRQ_CENTRAL_CONNECT:
            self.conn_handle, _, _ = data
            print("MIDI 设备已连接")
            led_pin.on()
            self.connected = True
            self.notifications_enabled = False
        elif event == _IRQ_CENTRAL_DISCONNECT:
            self.conn_handle = None
            print("MIDI 设备断开，重新广播...")
            self.connected = False
            led_pin.off()
            self.ble.gap_advertise(100, adv_data=self._advertise_payload())
        elif event == _IRQ_GATTS_WRITE:
            conn_handle, attr_handle = data
            if conn_handle == self.conn_handle and attr_handle == self.midi_cccd:
                cccd = self.ble.gatts_read(self.midi_cccd)
                enabled = struct.unpack("<H", cccd)[0] & 1
                self.notifications_enabled = bool(enabled)
                state = "开启" if self.notifications_enabled else "关闭"
                print(f"通知{state}")

    def _register(self):
        """ 注册 BLE MIDI 服务 """
        midi_service = (
            MIDI_SERVICE_UUID,
            [
                (
                    MIDI_CHARACTERISTIC_UUID,
                    ubluetooth.FLAG_READ
                    | ubluetooth.FLAG_WRITE
                    | ubluetooth.FLAG_WRITE_NO_RESPONSE
                    | ubluetooth.FLAG_NOTIFY,
                )
            ],
        )
        # 注册服务并获得特征句柄
        ((self.midi_characteristic,),) = self.ble.gatts_register_services([midi_service])
        self.midi_cccd = self.midi_characteristic + 1  # Notify 特征的 CCCD 句柄
        print(f"MIDI 特征值 Handle: {self.midi_characteristic}")

        # 开始 BLE 广播
        self.ble.gap_advertise(100, adv_data=self._advertise_payload())

    def _advertise_payload(self):
        """ 生成 macOS 兼容的 BLE 广播数据 """
        name = b"EMIDI"
        uuid_bytes = bytes.fromhex("03B80E5AEDE84B33A7516CE34EC4C700")
        midi_uuid = bytes(reversed(uuid_bytes))
        flags = b'\x02\x01\x06'
        uuid_field = bytes([len(midi_uuid) + 1, 0x07]) + midi_uuid  # 完整128-bit服务UUID
        name_field = bytes([len(name) + 1, 0x09]) + name
        return flags + uuid_field + name_field

    def send_midi(self, status, note, velocity):
        """ 发送 MIDI 消息 """
        if not self.connected:
            print("MIDI 未连接，跳过发送")
            return

        try:
            timestamp = time.ticks_ms() & 0x1FFF  # 13-bit timestamp
            header = 0x80 | (timestamp >> 7)
            midi_packet = bytes((header, 0x80 | (timestamp & 0x7F), status, note, velocity))

            # 写入 BLE 特征值并通知
            self.ble.gatts_write(self.midi_characteristic, midi_packet)
            self.ble.gatts_notify(self.conn_handle, self.midi_characteristic, midi_packet)

            print(f"发送 MIDI: {midi_packet}")

        except OSError as e:
            print(f"BLE 发送失败: {e}")
            self.connected = False

# 运行 BLE MIDI 设备
midi_device = BLEMidi()

while True:
    if not midi_device.connected:
        time.sleep_ms(200)
        continue

    for delta_ticks, status, note, velocity in TRACK_EVENTS:
        if not midi_device.connected:
            break
        delay = ticks_to_ms(delta_ticks)
        if delay:
            time.sleep_ms(delay)
        midi_device.send_midi(status, note, velocity)

        event_type = status & 0xF0
        note_label = note_to_name(note)
        if event_type == 0x90 and velocity:
            print("Note On  {} (0x{:02X})".format(note_label, note))
        elif event_type == 0x80 or velocity == 0:
            print("Note Off {} (0x{:02X})".format(note_label, note))


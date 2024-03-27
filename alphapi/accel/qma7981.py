"""
MicroPython I2C driver for QMA7981 6-axis motion tracking device
"""

__version__ = "0.1.0"

# pylint: disable=import-error
import ustruct
import utime
from machine import SoftI2C, Pin
from micropython import const

# pylint: enable=import-error

_WHO_AM_I = const(0x00)
_ACCEL_XOUT_L = const(0x01)
_ACCEL_XOUT_H = const(0x02)
_ACCEL_YOUT_L = const(0x03)
_ACCEL_YOUT_H = const(0x04)
_ACCEL_ZOUT_L = const(0x05)
_ACCEL_ZOUT_H = const(0x06)
_STEP_CNT_L = const(0x07)
_INT_STAT0 = const(0x08)
_INT_STAT1 = const(0x09)
_INT_STAT2 = const(0x0A)
_INT_STAT3 = const(0x0B)
_FIFO_STATE = const(0x0C)
_STEP_CNT_M = const(0x0D)
_REG_RANGE = const(0x0E)
_REG_BW_ODR = const(0x10)
_REG_POWER_CTL = const(0x11)
_STEP_SAMPLE_CNT = const(0x12)
_STEP_PRECISION = const(0x13)
_STEP_TIME_LOW = const(0x14)
_STEP_TIME_UP = const(0x15)
_INTPIN_CFG = const(0x20)
_INT_CFG = const(0x21)
_OS_CUST_X = const(0x27)
_OS_CUST_Y = const(0x28)
_OS_CUST_Z = const(0x29)


#ODR SET @lower ODR
QMA6981_ODR_1000HZ = 0x07
QMA6981_ODR_500HZ = 0x06
QMA6981_ODR_250HZ = 0x05
QMA6981_ODR_125HZ = 0x04  
QMA6981_ODR_62HZ = 0x03   
QMA6981_ODR_31HZ = 0x02   
QMA6981_ODR_16HZ = 0x01
QMA6981_ODR_HIGH = 0x20


#_ACCEL_FS_MASK = const(0b00011000)
ACCEL_FS_SEL_2G = const(0b0001)
ACCEL_FS_SEL_4G = const(0b0010)
ACCEL_FS_SEL_8G = const(0b0100)
ACCEL_FS_SEL_16G = const(0b1000)
ACCEL_FS_SEL_32G = const(0b1111)

#bandwidth
MCLK_DIV_BY_7695 = const(0b000)
MCLK_DIV_BY_3855 = const(0b001)
MCLK_DIV_BY_1935 = const(0b010)
MCLK_DIV_BY_975 = const(0b011)
MCLK_DIV_BY_15375 = const(0b101)
MCLK_DIV_BY_30735 = const(0b110)
MCLK_DIV_BY_61455 = const(0b111)

#Clock freq
CLK_500_KHZ = 0b0001
CLK_333_KHZ = 0b0000
CLK_200_KHZ = 0b0010
CLK_100_KHZ = 0b0011
CLK_50_KHZ = 0b0100
CLK_25_KHZ = 0b0101
CLK_12_KHZ_5 = 0b0110
CLK_5_KHZ = 0b0111


# no motion duration
NO_MOTION_1_SEC = 0b000000
NO_MOTION_2_SEC = 0b000001
NO_MOTION_3_SEC = 0b000010
NO_MOTION_5_SEC = 0b000100
NO_MOTION_10_SEC = 0b001001
NO_MOTION_15_SEC = 0b001110
NO_MOTION_30_SEC = 0b010010
NO_MOTION_1_MIN = 0b011000
NO_MOTION_2_MIN = 0b100010
NO_MOTION_3_MIN = 0b101000
NO_MOTION_4_MIN = 0b101110

# any motion sample
NUM_SAMPLES_1 = 0b00
NUM_SAMPLES_2 = 0b01
NUM_SAMPLES_3 = 0b10
NUM_SAMPLES_4 = 0b11

# power mode
MODE_STANDBY = 0
MODE_ACTIVE = 1

# motion detect
MOTION_DETECT_NOTHING = 0
MOTION_DETECT_ANY_MOTION = 1
MOTION_DETECT_NO_MOTION = 2

_ACCEL_SO_2G = 16384 # 1 / 16384 ie. 0.061 mg / digit
_ACCEL_SO_4G = 8192 # 1 / 8192 ie. 0.122 mg / digit
_ACCEL_SO_8G = 4096 # 1 / 4096 ie. 0.244 mg / digit
_ACCEL_SO_16G = 2048 # 1 / 2048 ie. 0.488 mg / digit
_ACCEL_SO_32G = 1024


SF_G = 1
SF_M_S2 = 9.80665 # 1 g = 9.80665 m/s2 ie. standard gravity
SF_DEG_S = 1
SF_RAD_S = 0.017453292519943 # 1 deg/s is 0.017453292519943 rad/s

class QMA7981:
    """Class which provides interface to QMA8981 6-axis motion tracking device."""
    def __init__(
        self, i2c, address=0x12,
        accel_fs=ACCEL_FS_SEL_2G, accel_sf=SF_M_S2,
    ):
        self.i2c = i2c
        self.address = address

        # 0x70 = standalone MPU6500, 0x71 = MPU6250 SIP, 0x90 = MPU6700
        if self.whoami not in [0xE7, 0xE8]:
            raise RuntimeError("QMA8981 not found in I2C bus.")

        # Reset, disable sleep mode
        self._register_char(_REG_POWER_CTL, 0x40)
        utime.sleep_ms(100)
        self._register_char(_REG_POWER_CTL, 0x80)
        utime.sleep_ms(100)

        self._accel_so = self._accel_fs(accel_fs)
        self._accel_sf = accel_sf

    @property
    def acceleration(self):
        """
        Acceleration measured by the sensor. By default will return a
        3-tuple of X, Y, Z axis acceleration values in m/s^2 as floats. Will
        return values in g if constructor was provided `accel_sf=SF_M_S2`
        parameter.
        """
        so = self._accel_so
        sf = self._accel_sf

        xyz = self._register_three_shorts(_ACCEL_XOUT_H)
        return tuple([value / so * sf for value in xyz])


    @property
    def whoami(self):
        """ Value of the whoami register. """
        return self._register_char(_WHO_AM_I)



    def _register_short(self, register, value=None, buf=bytearray(2)):
        if value is None:
            self.i2c.readfrom_mem_into(self.address, register, buf)
            return ustruct.unpack(">h", buf)[0]

        ustruct.pack_into(">h", buf, 0, value)
        return self.i2c.writeto_mem(self.address, register, buf)

    def _register_three_shorts(self, register, buf=bytearray(6)):
        self.i2c.readfrom_mem_into(self.address, register, buf)
        return ustruct.unpack(">hhh", buf)

    def _register_char(self, register, value=None, buf=bytearray(1)):
        if value is None:
            self.i2c.readfrom_mem_into(self.address, register, buf)
            return buf[0]

        ustruct.pack_into("<b", buf, 0, value)
        return self.i2c.writeto_mem(self.address, register, buf)

    def _accel_fs(self, value):
        #self._register_char(_ACCEL_CONFIG, value)

        # Return the sensitivity divider
        if ACCEL_FS_SEL_2G == value:
            return _ACCEL_SO_2G
        elif ACCEL_FS_SEL_4G == value:
            return _ACCEL_SO_4G
        elif ACCEL_FS_SEL_8G == value:
            return _ACCEL_SO_8G
        elif ACCEL_FS_SEL_16G == value:
            return _ACCEL_SO_16G

    def __enter__(self):
        return self

    def __exit__(self, exception_type, exception_value, traceback):
        pass


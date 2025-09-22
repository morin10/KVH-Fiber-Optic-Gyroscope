#!/usr/bin/env python3
import serial, struct, math, time, threading
import rospy
from std_msgs.msg import Float32, Float64

class DSP3000(threading.Thread):
    def __init__(self, port="/dev/ttyUSB0", baud=38400):
        super().__init__()
        self.daemon = True
        self.ser = serial.Serial(port, baud, timeout=1)

        self.pub_rate = rospy.Publisher("x_angular_rate", Float64, queue_size=10)
        self.pub_pitch = rospy.Publisher("pitch", Float32, queue_size=10)

        self.pitch_deg = 0.0
        self.last_time = None

        rospy.loginfo("DSP3000 driver started on %s @ %d", port, baud)

    def run(self):
        while not rospy.is_shutdown():
            line = self.ser.readline()
            if not line:
                continue

            data = line.decode(errors="ignore").strip().split()
            if len(data) < 2:
                continue

            try:
                x_rate = float(data[0])   # deg/s
                validity = int(data[1])
            except ValueError:
                rospy.logwarn(f"DSP3000 invalid data: {data}")
                continue

            now = time.time()
            if self.last_time is not None:
                dt = now - self.last_time
                # pitch 적분
                self.pitch_deg += x_rate * dt
                # wrap-around (-180 ~ +180)
                self.pitch_deg = (self.pitch_deg + 180.0) % 360.0 - 180.0
                self.pub_pitch.publish(Float32(self.pitch_deg))

            self.last_time = now

            # publish raw x_rate
            self.pub_rate.publish(x_rate)

        self.ser.close()


class DSP1760(threading.Thread):
    def __init__(self, port="/dev/ttyUSB1", baud=115200,
                 frame_len=36, header_hex="FE81FF55", axis_offset=12,
                 deg_units=True, bias_deg=0.0, invert=False):
        super().__init__()
        self.daemon = True
        self.ser = serial.Serial(port, baud, timeout=0.01)
        self.ser.reset_input_buffer()

        self.frame_len = frame_len
        self.hdr = bytes.fromhex(header_hex)
        self.axis_offset = axis_offset
        self.deg_units = deg_units
        self.bias_deg = bias_deg
        self.invert = invert

        self.buf = bytearray()

        self.pub_z = rospy.Publisher("z_angular_rate", Float32, queue_size=10)
        self.pub_yaw = rospy.Publisher("yaw", Float32, queue_size=10)

        self.yaw_deg = 0.0
        self.last_time = None

        rospy.loginfo("DSP1760 driver started on %s @ %d", port, baud)

    def _process_frame(self, frame):
        z = struct.unpack_from(">f", frame, self.axis_offset)[0]
        if not self.deg_units:
            z = z * (180.0/math.pi)
        z_deg = (-z if self.invert else z) - self.bias_deg

        now = rospy.Time.now()
        if self.last_time is not None:
            dt = (now - self.last_time).to_sec()
            # yaw 적분
            self.yaw_deg += z_deg * dt
            self.yaw_deg = (self.yaw_deg + 180.0) % 360.0 - 180.0
            self.pub_yaw.publish(Float32(self.yaw_deg))

        self.last_time = now

        # 퍼블리시
        self.pub_z.publish(Float32(z_deg))

    def run(self):
        while not rospy.is_shutdown():
            chunk = self.ser.read(4096)
            if chunk:
                self.buf.extend(chunk)
            while True:
                i = self.buf.find(self.hdr)
                if i < 0 or len(self.buf) < i + self.frame_len:
                    break
                frame = bytes(self.buf[i:i+self.frame_len])
                del self.buf[:i+self.frame_len]
                self._process_frame(frame)
        self.ser.close()


if __name__ == "__main__":
    rospy.init_node("gyro")

    dsp3000 = DSP3000()
    dsp1760 = DSP1760()

    dsp3000.start()
    dsp1760.start()

    rospy.spin()
